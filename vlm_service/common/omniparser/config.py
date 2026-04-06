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
    mathpix_api_key = os.getenv("MATHPIX_API_KEY", "")
    mathpix_app_id = os.getenv("MATHPIX_APP_ID", "")
    mathpix_endpoint = os.getenv("MATHPIX_ENDPOINT", "https://api.mathpix.com/v3/text")
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
        settings.mathpix_api_key = config.get("mathpix_api_key", settings.mathpix_api_key)
        settings.mathpix_app_id = config.get("mathpix_app_id", settings.mathpix_app_id)
        settings.mathpix_endpoint = config.get("mathpix_endpoint", settings.mathpix_endpoint)
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
