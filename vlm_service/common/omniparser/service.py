from __future__ import annotations

import io
import os
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

# Stabilize PaddleOCR on this environment before parser utilities import Paddle.
_project_root = Path(__file__).resolve().parents[3]
_paddlex_cache_home = _project_root / ".model_cache" / "paddlex"
_paddlex_cache_home.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(_paddlex_cache_home))

from .config import Settings
from .core.parser_utils import check_ocr_box, get_easyocr_reader, get_paddle_ocr, get_som_labeled_img, get_yolo_model
from .schemas import BoundingBox, Control, ControlsResponse, Point


def _strip_data_url(value: str) -> str:
    if value.startswith("data:"):
        return value.split(",", 1)[1]
    return value


class OmniParserService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self._som_model = None

    @property
    def loaded(self) -> bool:
        return self._som_model is not None

    def load_model(self) -> None:
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        if self._som_model is not None:
            return
        self._som_model = get_yolo_model(model_path=str(self.settings.som_model_path))

    def _decode_image(
        self,
        image_base64: str | None = None,
        image_url: str | None = None,
        image: Image.Image | None = None,
    ) -> Image.Image:
        if image is not None:
            return image.convert("RGB")

        payload = image_base64 or image_url
        if not payload:
            raise ValueError("Provide image, image_base64, or image_url.")

        clean_payload = _strip_data_url(payload)
        image_bytes = base64.b64decode(clean_payload)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return image

    @staticmethod
    def _build_control(index: int, raw_control: dict) -> Control:
        x1, y1, x2, y2 = raw_control["bbox"]
        return Control(
            id=index,
            type=raw_control.get("type", "unknown"),
            interactivity=bool(raw_control.get("interactivity", False)),
            content=raw_control.get("content"),
            source=raw_control.get("source"),
            bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
            center=Point(x=(x1 + x2) / 2, y=(y1 + y2) / 2),
        )

    def _enrich_control_content(self, image: Image.Image, parsed_content_list: list[dict]) -> list[dict]:
        width, height = image.size
        ocr_client = None

        for control in parsed_content_list:
            if control.get("content"):
                continue
            if control.get("type") != "icon":
                continue

            x1, y1, x2, y2 = control["bbox"]
            left = max(0, min(width, int(x1 * width)))
            top = max(0, min(height, int(y1 * height)))
            right = max(0, min(width, int(x2 * width)))
            bottom = max(0, min(height, int(y2 * height)))

            if right - left < 6 or bottom - top < 6:
                continue

            crop = image.crop((left, top, right, bottom))
            texts, ocr_client = self._read_crop_text(crop, ocr_client=ocr_client)
            if texts:
                control["content"] = texts[0]
                control["source"] = f"{control.get('source', 'box_yolo_content_yolo')}_{self.settings.ocr_backend}_crop_ocr"

        return parsed_content_list

    def _read_crop_text(self, crop: Image.Image, ocr_client=None) -> tuple[list[str], object]:
        backend = self.settings.ocr_backend
        crop_np = np.array(crop)

        if backend == "paddleocr":
            if ocr_client is None:
                ocr_client = get_paddle_ocr(device=self.settings.device)
            try:
                result = ocr_client.ocr(
                    crop_np,
                    text_rec_score_thresh=0.2,
                )
            except Exception:
                return [], ocr_client
            texts = self._extract_texts_from_paddle_result(result)
            return texts, ocr_client

        
        if ocr_client is None:
            ocr_client = get_easyocr_reader(device=self.settings.device)

        try:
            results = ocr_client.readtext(
                crop_np,
                text_threshold=0.2,
                low_text=0.1,
                allowlist="0123456789+-=*/%.",
            )
        except Exception:
            return [], ocr_client

        texts = [item[1].strip() for item in results if len(item) > 1 and item[1].strip()]
        return texts, ocr_client

    @staticmethod
    def _extract_texts_from_paddle_result(result) -> list[str]:
        texts: list[str] = []

        def walk(node):
            if node is None:
                return

            if isinstance(node, dict):
                rec_texts = node.get("rec_texts")
                if rec_texts is not None:
                    texts.extend([text.strip() for text in rec_texts if isinstance(text, str) and text.strip()])
                    return
                for value in node.values():
                    walk(value)
                return

            if hasattr(node, "keys") and hasattr(node, "get"):
                try:
                    walk(dict(node))
                    return
                except Exception:
                    pass

            if hasattr(node, "json") and not isinstance(node, (str, bytes)):
                try:
                    json_value = node.json
                    if callable(json_value):
                        json_value = json_value()
                    walk(json_value)
                    return
                except Exception:
                    pass

            if isinstance(node, (list, tuple)):
                if (
                    len(node) > 1
                    and isinstance(node[1], (list, tuple))
                    and len(node[1]) > 0
                    and isinstance(node[1][0], str)
                ):
                    text = node[1][0].strip()
                    if text:
                        texts.append(text)
                        return
                for item in node:
                    walk(item)

        walk(result)
        return texts

    
    def parse_controls(
        self,
        image_base64: str | None = None,
        image_url: str | None = None,
        image: Image.Image | None = None,
        include_grounded_image: bool = False,
    ) -> ControlsResponse:
        self._ensure_loaded()
        image = self._decode_image(image_base64=image_base64, image_url=image_url, image=image)
        width, height = image.size

        box_overlay_ratio = max(image.size) / 3200
        draw_bbox_config = {
            "text_scale": 0.8 * box_overlay_ratio,
            "text_thickness": max(int(2 * box_overlay_ratio), 1),
            "text_padding": max(int(3 * box_overlay_ratio), 1),
            "thickness": max(int(3 * box_overlay_ratio), 1),
        }

        start = time.time()
        (ocr_text, ocr_bbox), _ = check_ocr_box(
            image,
            display_img=False,
            output_bb_format="xyxy",
            easyocr_args={"text_threshold": 0.8},
            device=self.settings.device,
            ocr_backend=self.settings.ocr_backend if self.settings.ocr_backend in {"easyocr", "paddleocr"} else "easyocr",
        )
        grounded_image_base64, _, parsed_content_list = get_som_labeled_img(
            image,
            self._som_model,
            BOX_TRESHOLD=self.settings.box_threshold,
            output_coord_in_ratio=True,
            ocr_bbox=ocr_bbox,
            draw_bbox_config=draw_bbox_config,
            caption_model_processor=None,
            ocr_text=ocr_text,
            use_local_semantics=False,
            iou_threshold=getattr(self.settings, 'iou_threshold', 0.1),
            scale_img=True,
            batch_size=128,
            device=self.settings.device,
            pixel_threshold=getattr(self.settings, 'control_merge_pixel_threshold', 10),
            merge_threshold=getattr(self.settings, 'control_merge_threshold', 25),
            resolution_scale=getattr(self.settings, 'detection_resolution_scale', 1.0),
        )
        parsed_content_list = self._enrich_control_content(image, parsed_content_list)
        controls = [self._build_control(index, raw_control) for index, raw_control in enumerate(parsed_content_list)]
        return ControlsResponse(
            model=self.settings.default_model,
            device=self.settings.device,
            image_width=width,
            image_height=height,
            control_count=len(controls),
            controls=controls,
            grounded_image_base64=grounded_image_base64 if include_grounded_image else None,
            latency_seconds=round(time.time() - start, 4),
        )


service = OmniParserService()
