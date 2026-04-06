import torch
import re
import os
import sys
from PIL import Image

# Ensure the project root is on sys.path regardless of launch directory.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from vlm_service.common.base import BaseVisionWrapper
from vlm_service.prompts.scale import AGENT_PROMPT

class HuggingFaceVisionWrapper(BaseVisionWrapper):
    def __init__(self, config: dict):
        self.model_id = config.get("model_id", "OpenGVLab/ScaleCUA-3B")
        self.device_map = config.get("device_map", "cuda")
        self.model = None
        self.processor = None

    def load_model(self):
        if self.model is None:
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
            print(f"[HF Wrapper] Booting {self.model_id} into System VRAM. This may take several minutes on cold boot!")
            self.processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True)
            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                self.model_id, torch_dtype=torch.float16, device_map=self.device_map, trust_remote_code=True
            )
            print("[HF Wrapper] 🟢 HuggingFace pipeline securely mapped to GPU!")

    def find_control(self, query: str, action_type: str, image: Image.Image) -> dict:
        self.load_model()
        from qwen_vl_utils import process_vision_info
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": f"{AGENT_PROMPT}\n\nTask: Find the UI element described exactly as '{query}'. Generate the precise coordinate action corresponding to '{action_type}' for this element."}
                ]
            }
        ]
        
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt"
        ).to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=100)
            
        response_text = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]
        
        action_match = re.search(r"<action>(.*?)</action>", response_text, re.DOTALL)
        if action_match:
            action_code = action_match.group(1).strip()
            x_match = re.search(r"x\s*=\s*(\d+(?:\.\d+)?)", action_code) or re.search(r"\((\d+)\s*,", action_code)
            y_match = re.search(r"y\s*=\s*(\d+(?:\.\d+)?)", action_code) or re.search(r",\s*(\d+)\)", action_code)
            if x_match and y_match:
                x = int(float(x_match.group(1)))
                y = int(float(y_match.group(1)))
                return {"status": "success", "coordinates": {"x": x, "y": y}, "raw_response": response_text, "parsed_action": action_code}
        return {"status": "failed", "reason": "No discrete bounding box coordinates were located.", "raw_response": response_text}
