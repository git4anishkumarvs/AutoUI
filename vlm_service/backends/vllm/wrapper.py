import base64
import json
import os
import re
import sys
from io import BytesIO

import requests
from PIL import Image

# Ensure the project root is on sys.path regardless of launch directory.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from vlm_service.common.base import BaseVisionWrapper
from vlm_service.prompts.vllm_scale import AGENT_PROMPT


class VLLMVisionWrapper(BaseVisionWrapper):
    def __init__(self, config: dict):
        self.api_base = config.get("api_base", "http://localhost:8030/v1").rstrip("/")
        self.model_name = config.get("model_name", "OpenGVLab/ScaleCUA-3B")
        self.api_key = config.get("api_key", "")
        self.max_tokens = int(config.get("max_tokens", 512))
        self.temperature = float(config.get("temperature", 0))
        self.top_p = float(config.get("top_p", 0.9))
        self.verified = False
        self.prompt = AGENT_PROMPT

    def load_model(self):
        response = requests.get(
            f"{self.api_base}/models", 
            headers=self._headers(), 
            timeout=5
        )
        response.raise_for_status()
        self.verified = True
        print(f"[vLLM Wrapper] API {self.api_base} successfully pinged!")

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_chat_curl_command(self, payload: dict) -> str:
        import copy

        payload_copy = copy.deepcopy(payload)
        for msg in payload_copy.get("messages", []):
            if isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        url = item["image_url"]["url"]
                        if url.startswith("data:image/png;base64,"):
                            item["image_url"]["url"] = url[:40] + "...[truncated]..."

        payload_json = json.dumps(payload_copy, separators=(",", ":"))
        header_parts = ['-H "Content-Type: application/json"']
        if self.api_key:
            header_parts.append(f'-H "Authorization: Bearer {self.api_key}"')

        return (
            f'curl -X POST "{self.api_base}/chat/completions" '
            f"{' '.join(header_parts)} "
            f"-d '{payload_json}'"
        )

    def _build_user_prompt(self, query: str, action_type: str, image: Image.Image) -> str:
        action_name = "click" if action_type == "click" else "type_text"
        img_w, img_h = image.size

        return (
            "Focus only on locating the requested UI element in the screenshot.\n"
            f"Task: Find the UI element described exactly as '{query}'.\n"
            f"Return exactly one <action> tag with this format: "
            f"<action>{action_name}(x=123, y=456)</action>.\n"
            f"Use integer pixel coordinates in the {img_w}x{img_h} screenshot space.\n"
            "Do not ask follow-up questions. Do not return multiple actions. "
            "Do not return markdown or extra commentary."
        )

    def find_control(self, query: str, action_type: str, image: Image.Image = None) -> dict:
        if image is None:
            raise ValueError("vLLM backend requires an image for UI grounding")

        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_str}"},
                        },
                        {"type": "text", "text": self._build_user_prompt(query, action_type, image)},
                    ],
                },
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }

        print(f"[vLLM Wrapper] curl => {self._build_chat_curl_command(payload)}")

        response = requests.post(
            f"{self.api_base}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=120,
        )

        if response.status_code != 200:
            print("[vLLM ERROR RAW]:", response.text)

        response.raise_for_status()

        data = response.json()
        response_text = data["choices"][0]["message"]["content"]

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
