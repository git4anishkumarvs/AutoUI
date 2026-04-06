from __future__ import annotations

import base64
import io
import time

import torch
from PIL import Image

from .config import Settings
from .core.parser_utils import check_ocr_box, get_som_labeled_img, get_yolo_model
from .schemas import BoundingBox, Control, ControlsResponse, Point


def _strip_data_url(value: str) -> str:
    if value.startswith("data:"):
        return value.split(",", 1)[1]
    return value


class OmniParserService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self._som_model = None

    def _ensure_loaded(self) -> None:
        if self._som_model is not None:
            return
        self._som_model = get_yolo_model(model_path=str(self.settings.som_model_path))

    def _decode_image(self, image_base64: str | None = None, image_url: str | None = None) -> Image.Image:
        payload = image_base64 or image_url
        if not payload:
            raise ValueError("Provide image_base64 or image_url.")

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

    def parse_controls(
        self,
        image_base64: str | None = None,
        image_url: str | None = None,
        include_grounded_image: bool = False,
    ) -> ControlsResponse:
        self._ensure_loaded()
        image = self._decode_image(image_base64=image_base64, image_url=image_url)
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
            iou_threshold=0.7,
            scale_img=False,
            batch_size=128,
            device=self.settings.device,
        )
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
