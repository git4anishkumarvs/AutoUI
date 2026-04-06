import io
import json
import os
import sys

# Ensure the project root (parent of vlm_service/) is on sys.path regardless of
# which directory uvicorn / python is launched from.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from PIL import Image
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="AutoUI Remote Vision Proxy API")

def load_runtime_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(config_path):
        raise RuntimeError(f"Config not found at {config_path}")

    with open(config_path, "r") as f:
        return json.load(f)

def get_vlm_wrapper():
    """ Determines which AI engine logic to hot-swap dynamically from config """
    config = load_runtime_config()
    backend = config.get("backend", "huggingface")
    print(f"[Architecture Router] Mounting abstraction wrapper for active backend mode: {backend.upper()}")
    
    if backend == "huggingface":
        from vlm_service.backends.huggingface.wrapper import HuggingFaceVisionWrapper
        return HuggingFaceVisionWrapper(config.get("huggingface", {}))
    elif backend == "openai_compatible":
        from vlm_service.backends.openai.wrapper import OpenAIVisionWrapper
        return OpenAIVisionWrapper(config.get("openai_compatible", {}))
    elif backend in ("vllm", "vllm_compatible"):
        from vlm_service.backends.vllm.wrapper import VLLMVisionWrapper
        return VLLMVisionWrapper(config.get("vllm", config.get("vllm_compatible", {})))
    elif backend == "omniparser":
        from vlm_service.backends.omniparser.wrapper import OmniParserVisionWrapper
        return OmniParserVisionWrapper(config.get("omniparser", {}))
    else:
        raise ValueError(f"Unknown polymorphic VLM backend requested: {backend}")


def _decode_uploaded_image(img_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(img_bytes)).convert("RGB")

# Globals orchestrators
vlm_wrapper = None
vlm_backend = None

def ensure_vlm_wrapper():
    global vlm_wrapper, vlm_backend
    config = load_runtime_config()
    backend = config.get("backend", "huggingface")

    if vlm_wrapper is None or vlm_backend != backend:
        vlm_wrapper = get_vlm_wrapper()
        vlm_backend = backend

    return vlm_wrapper, config

@app.get("/status")
async def get_status():
    # Always re-read config.json so display is live with any edits
    try:
        config = load_runtime_config()
    except Exception:
        return {"loaded": False, "status": "Config not found", "backend": "unknown", "display_name": "Unknown"}

    backend = config.get("backend", "unknown")
    
    if backend == "huggingface":
        model_id = config.get("huggingface", {}).get("model_id", "Unknown Model")
        display_name = model_id
        global vlm_wrapper, vlm_backend
        if vlm_wrapper is None or vlm_backend != backend:
            try:
                vlm_wrapper, _ = ensure_vlm_wrapper()
            except Exception:
                pass
        is_loaded = vlm_wrapper is not None and getattr(vlm_wrapper, "model", None) is not None
        status = "Loaded into GPU" if is_loaded else "Cold - Not Yet Loaded"
        return {"loaded": is_loaded, "status": status, "backend": backend, "display_name": display_name}
        
    elif backend == "openai_compatible":
        api_base = config.get("openai_compatible", {}).get("api_base", "Unknown Endpoint")
        model_name = config.get("openai_compatible", {}).get("model_name", "Unknown Model")
        display_name = f"{model_name} @ {api_base}"
        is_verified = (
            vlm_wrapper is not None
            and vlm_backend == backend
            and getattr(vlm_wrapper, "verified", False)
        )
        status = "API connection verified" if is_verified else "Proxy - Pending Verification"
        return {"loaded": is_verified, "status": status, "backend": backend, "display_name": display_name}
        
    elif backend in ("vllm", "vllm_compatible"):
        vllm_config = config.get("vllm", config.get("vllm_compatible", {}))
        api_base = vllm_config.get("api_base", "Unknown Endpoint")
        model_name = vllm_config.get("model_name", "Unknown Model")
        display_name = f"{model_name} @ {api_base}"
        is_verified = (
            vlm_wrapper is not None
            and vlm_backend == backend
            and getattr(vlm_wrapper, "verified", False)
        )
        status = "API connection verified" if is_verified else "vLLM - Pending Verification"
        return {"loaded": is_verified, "status": status, "backend": backend, "display_name": display_name}
    elif backend == "omniparser":
        omniparser_config = config.get("omniparser", {})
        display_name = omniparser_config.get("display_name", "OmniParser")
        is_loaded = (
            vlm_wrapper is not None
            and vlm_backend == backend
            and bool(getattr(vlm_wrapper, "is_loaded", False))
        )
        status = "Loaded into memory" if is_loaded else "Cold - Not Yet Loaded"
        return {"loaded": is_loaded, "status": status, "backend": backend, "display_name": display_name}
    
    return {"loaded": False, "status": "Unknown backend in config.json", "backend": backend, "display_name": "Unknown"}

@app.get("/warmup")
async def warmup():
    try:
        wrapper, config = ensure_vlm_wrapper()
        wrapper.load_model()

        backend = config.get("backend", "unknown")
        if backend == "huggingface":
            status = "Loaded into GPU"
        elif backend in ("openai_compatible", "vllm", "vllm_compatible"):
            status = "API connection verified"
        elif backend == "omniparser":
            status = "Loaded into memory"
        else:
            status = "Ready"

        return JSONResponse(
            {
                "status": "success",
                "backend": backend,
                "loaded": True,
                "message": status,
            }
        )
    except Exception as e:
        print(f"Warmup Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/find_control")
async def find_control(
    query: str = Form(...),
    action_type: str = Form("click"),
    screenshot: UploadFile = File(...)
):
    try:
        global vlm_wrapper
        # Keep runtime wrapper aligned with the latest config.json backend choice.
        vlm_wrapper, _ = ensure_vlm_wrapper()
            
        # Decode physical bytes from the stream interface
        img_bytes = await screenshot.read()
        image = _decode_uploaded_image(img_bytes)
        
        # Transparently pipe into the respective active ML inference engine
        result = vlm_wrapper.find_control(query, action_type, image)
        print(f"API Output Node Resolved: {result['status']}")
        return result
            
    except Exception as e:
        print(f"Backend Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/find_controls")
async def find_controls(
    screenshot: UploadFile = File(...),
    include_grounded_image: bool = Form(False)
):
    try:
        global vlm_wrapper
        vlm_wrapper, _ = ensure_vlm_wrapper()

        img_bytes = await screenshot.read()
        image = _decode_uploaded_image(img_bytes)
        return vlm_wrapper.list_controls(image, include_grounded_image=include_grounded_image)
    except NotImplementedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Backend Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ground_controls")
async def ground_controls(
    screenshot: UploadFile = File(...)
):
    try:
        global vlm_wrapper
        vlm_wrapper, _ = ensure_vlm_wrapper()

        img_bytes = await screenshot.read()
        image = _decode_uploaded_image(img_bytes)
        return vlm_wrapper.list_controls(image, include_grounded_image=True)
    except NotImplementedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Backend Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
