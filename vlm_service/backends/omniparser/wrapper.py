import json
import os
import re
import sys

from PIL import Image

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from vlm_service.common.base import BaseVisionWrapper
from vlm_service.common.omniparser import OmniParserService, Settings


class OmniParserVisionWrapper(BaseVisionWrapper):
    def __init__(self, config: dict):
        self.settings = Settings.from_config(config)
        self.service = OmniParserService(self.settings)

    @property
    def is_loaded(self) -> bool:
        return self.service.loaded

    def load_model(self) -> None:
        self.service.load_model()

    def list_controls(self, image: Image.Image, include_grounded_image: bool = False) -> dict:
        parsed = self.service.parse_controls(image=image, include_grounded_image=include_grounded_image)
        return parsed.model_dump()

    def find_control(self, query: str, action_type: str, image: Image.Image) -> dict:
        parsed = self.service.parse_controls(image=image, include_grounded_image=False)
        matched_control, score = self._select_best_control(parsed.controls, query, action_type)
        raw_response = json.dumps(parsed.model_dump(), ensure_ascii=True)

        if matched_control is None:
            return {
                "status": "failed",
                "reason": f"No matching control was located for query '{query}'.",
                "raw_response": raw_response,
            }

        x = int(round(matched_control.center.x * parsed.image_width))
        y = int(round(matched_control.center.y * parsed.image_height))
        action_name = "click" if action_type == "click" else "type_text"

        return {
            "status": "success",
            "coordinates": {"x": x, "y": y},
            "raw_response": raw_response,
            "parsed_action": f"{action_name}(x={x}, y={y})",
            "matched_control": matched_control.model_dump(),
            "match_score": score,
        }

    @staticmethod
    def _normalize(value: str | None) -> str:
        value = (value or "").lower().strip()
        return re.sub(r"\s+", " ", value).strip()

    @classmethod
    def _tokenize(cls, value: str | None) -> list[str]:
        normalized = cls._normalize(value)
        return [token for token in normalized.split() if token]

    @classmethod
    def _score_control(cls, control, query: str, action_type: str) -> int:
        raw_query = (query or "").strip().lower()
        normalized_query = cls._normalize(query)
        raw_content = (control.content or "").strip().lower()
        if not normalized_query:
            return -1

        query_tokens = cls._tokenize(query)
        content = cls._normalize(control.content)
        haystack = cls._normalize(" ".join(part for part in [control.content, control.type, control.source, str(control.id)] if part))
        haystack_tokens = set(cls._tokenize(haystack))

        score = 0
        if raw_query and raw_content and raw_query == raw_content:
            score += 260
        if raw_query and raw_content and raw_query in raw_content:
            score += 160
        if normalized_query == str(control.id):
            score += 250
        if content and normalized_query == content:
            score += 220
        if content and normalized_query in content:
            score += 140
        if normalized_query in haystack:
            score += 100

        overlap_count = sum(1 for token in query_tokens if token in haystack_tokens)
        if query_tokens and overlap_count == len(query_tokens):
            score += 80 + 5 * overlap_count
        else:
            score += 18 * overlap_count

        if control.interactivity and action_type in ("click", "type"):
            score += 15
        if control.type == "text" and action_type == "type":
            score += 12
        if control.type == "icon" and action_type == "click":
            score += 8
        if control.content:
            score += 5
        return score

    @classmethod
    def _select_best_control(cls, controls, query: str, action_type: str):
        ranked = sorted(
            ((cls._score_control(control, query, action_type), control) for control in controls),
            key=lambda item: item[0],
            reverse=True,
        )
        if not ranked:
            return None, None
        best_score, best_control = ranked[0]
        if best_score < 25:
            return None, best_score
        return best_control, best_score
