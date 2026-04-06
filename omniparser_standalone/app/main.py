from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, HTTPException

from .config import Settings
from .schemas import ControlsResponse, ImageRequest, OpenAIResponsesRequest
from .service import service


settings = Settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)


def _extract_image_from_openai_request(request: OpenAIResponsesRequest) -> tuple[str | None, str | None]:
    image_base64 = None
    image_url = None

    for message in request.input:
        for item in message.content:
            if getattr(item, "type", None) != "input_image":
                continue
            image_base64 = getattr(item, "image_base64", None) or image_base64
            image_url = getattr(item, "image_url", None) or image_url
            if image_base64 or image_url:
                return image_base64, image_url

    return None, None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "device": settings.device}


@app.post("/api/v1/find-controls", response_model=ControlsResponse)
def find_controls(request: ImageRequest) -> ControlsResponse:
    try:
        return service.parse_controls(
            image_base64=request.image_base64,
            image_url=request.image_url,
            include_grounded_image=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/ground-controls", response_model=ControlsResponse)
def ground_controls(request: ImageRequest) -> ControlsResponse:
    try:
        return service.parse_controls(
            image_base64=request.image_base64,
            image_url=request.image_url,
            include_grounded_image=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/responses")
def openai_like_responses(request: OpenAIResponsesRequest) -> dict:
    image_base64, image_url = _extract_image_from_openai_request(request)
    include_grounded_image = (
        "grounded_image" in request.include
        or bool(request.metadata.get("include_grounded_image"))
    )

    if not image_base64 and not image_url:
        raise HTTPException(status_code=400, detail="No input_image item was found in the request.")

    try:
        parsed = service.parse_controls(
            image_base64=image_base64,
            image_url=image_url,
            include_grounded_image=include_grounded_image,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    control_lines = [
        f"{control.id}: type={control.type}, interactive={control.interactivity}, content={control.content}, bbox=({control.bbox.x1:.4f}, {control.bbox.y1:.4f}, {control.bbox.x2:.4f}, {control.bbox.y2:.4f})"
        for control in parsed.controls
    ]
    summary_text = "\n".join(control_lines) if control_lines else "No controls found."

    return {
        "id": f"resp_{uuid.uuid4().hex}",
        "object": "response",
        "created_at": int(time.time()),
        "model": request.model or settings.default_model,
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": summary_text},
                    {"type": "output_json", "json": parsed.model_dump()},
                ],
            }
        ],
        "status": "completed",
    }
