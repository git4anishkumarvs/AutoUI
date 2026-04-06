import requests
import base64
import re
import json
import os
import sys
from io import BytesIO
from PIL import Image

# Ensure the project root is on sys.path regardless of launch directory.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from vlm_service.common.base import BaseVisionWrapper
from vlm_service.prompts.scale import AGENT_PROMPT


class OpenAIVisionWrapper(BaseVisionWrapper):
    def __init__(self, config: dict):
        self.api_base = config.get("api_base", "http://localhost:1234/v1")
        self.model_name = config.get("model_name", "local-model")
        self.api_key = config.get("api_key", "lm-studio")
        self.verified = False

    def load_model(self):
        response = requests.get(
            f"{self.api_base}/models",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=2,
        )
        response.raise_for_status()
        self.verified = True
        print(f"[OpenAI Wrapper] API {self.api_base} successfully pinged!")

    def _build_chat_curl_command(self, payload: dict) -> str:
        import copy
        payload_copy = copy.deepcopy(payload)
        # Truncate base64 image strings for logging
        for msg in payload_copy.get("messages", []):
            if isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        url = item["image_url"]["url"]
                        if url.startswith("data:image/png;base64,"):
                            item["image_url"]["url"] = url[:40] + "...[truncated]..."

        payload_json = json.dumps(payload_copy, separators=(",", ":"))
        return (
            f'curl -X POST "{self.api_base}/chat/completions" '
            f'-H "Content-Type: application/json" '
            f'-H "Authorization: Bearer {self.api_key}" '
            f"-d '{payload_json}'"
        )

    def find_control(self, query: str, action_type: str, image: Image.Image = None) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        action_name = "click" if action_type == "click" else "type_text"
        
        # Use dynamic dimensions if image is provided, otherwise fallback to 1920x1080
        img_w, img_h = (image.width, image.height) if image else (1920, 1080)
        
        user_prompt = (
            f"Find the UI element described exactly as '{query}'. "
            f"Return only one tag in this exact format: "
            f"<action>{action_name}(x=123, y=456)</action>. "
            f"Use integer pixel coordinates in the {img_w}x{img_h} image space. "
            f"Do not include reasoning, explanations, markdown, or any extra text."
        )

        if image is not None:
            print("[Wrapper Mode] VISION MODE ENABLED")

            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

            user_content = [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_str}"},
                },
            ]

        else:
            print("[Wrapper Mode] TEXT-ONLY MODE (no image provided)")
            user_content = user_prompt

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": AGENT_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 300,
            "temperature": 0,
        }

        print(f"[OpenAI Wrapper] curl => {self._build_chat_curl_command(payload)}")

        response = requests.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=payload,
        )

        # Better error visibility
        if response.status_code != 200:
            print("[LM STUDIO ERROR RAW]:", response.text)

        response.raise_for_status()

        data = response.json()
        response_text = data["choices"][0]["message"]["content"]

        # Parse action
        action_match = re.search(r"<action>(.*?)</action>", response_text, re.DOTALL)
        if action_match:
            action_code = action_match.group(1).strip()

            x_match = re.search(r"x\s*=\s*(\d+(?:\.\d+)?)", action_code) or re.search(r"\((\d+)\s*,", action_code)
            y_match = re.search(r"y\s*=\s*(\d+(?:\.\d+)?)", action_code) or re.search(r",\s*(\d+)\)", action_code)

            if x_match and y_match:
                x = int(float(x_match.group(1)))
                y = int(float(y_match.group(1)))

                return {
                    "status": "success",
                    "coordinates": {"x": x, "y": y},
                    "raw_response": response_text,
                    "parsed_action": action_code,
                }

        return {
            "status": "failed",
            "reason": "No discrete bounding box coordinates were located.",
            "raw_response": response_text,
        }
