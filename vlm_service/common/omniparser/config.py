from __future__ import annotations

import os
from pathlib import Path

import torch


PROJECT_ROOT = Path(__file__).resolve().parent
WEIGHTS_ROOT = PROJECT_ROOT / "weights"

DEFAULT_SOM_MODEL_PATH = WEIGHTS_ROOT / "icon_detect" / "model.pt"
DEFAULT_CAPTION_MODEL_PATH = WEIGHTS_ROOT / "icon_caption_florence"


class Settings:
    app_name = "OmniParser"
    app_version = "0.1.0"
    default_model = "omniparser-autoui"
    caption_model_name = "florence2"
    box_threshold = 0.05
    ocr_backend = "easyocr"
    control_merge_pixel_threshold = 10
    control_merge_threshold = 25
    iou_threshold = 0.1
    detection_resolution_scale = 1.0
    requested_device = os.getenv("OMNIPARSER_DEVICE", "cuda")
    device = (
        "cuda"
        if requested_device == "cuda" and torch.cuda.is_available()
        else "cpu"
    )
    som_model_path = DEFAULT_SOM_MODEL_PATH
    caption_model_path = DEFAULT_CAPTION_MODEL_PATH

    @classmethod
    def from_config(cls, config: dict | None = None) -> "Settings":
        config = config or {}
        settings = cls()
        settings.box_threshold = float(config.get("box_threshold", settings.box_threshold))
        settings.ocr_backend = str(config.get("ocr_backend", settings.ocr_backend)).lower().strip()
        settings.control_merge_pixel_threshold = int(config.get("control_merge_pixel_threshold", settings.control_merge_pixel_threshold))
        settings.control_merge_threshold = int(config.get("control_merge_threshold", settings.control_merge_threshold))
        settings.iou_threshold = float(config.get("iou_threshold", settings.iou_threshold))
        settings.detection_resolution_scale = float(config.get("detection_resolution_scale", settings.detection_resolution_scale))
        settings.requested_device = config.get("device", settings.requested_device)
        settings.device = (
            "cuda"
            if settings.requested_device == "cuda" and torch.cuda.is_available()
            else "cpu"
        )

        if config.get("weights_root"):
            weights_root = Path(config["weights_root"])
            if not weights_root.is_absolute():
                project_root = Path(__file__).resolve().parents[3]
                weights_root = project_root / weights_root
            settings.som_model_path = weights_root / "icon_detect" / "model.pt"
            settings.caption_model_path = weights_root / "icon_caption_florence"
        if config.get("som_model_path"):
            som_model_path = Path(config["som_model_path"])
            if not som_model_path.is_absolute():
                project_root = Path(__file__).resolve().parents[3]
                som_model_path = project_root / som_model_path
            settings.som_model_path = som_model_path
        if config.get("caption_model_path"):
            caption_model_path = Path(config["caption_model_path"])
            if not caption_model_path.is_absolute():
                project_root = Path(__file__).resolve().parents[3]
                caption_model_path = project_root / caption_model_path
            settings.caption_model_path = caption_model_path
        return settings
