from __future__ import annotations

import os
from pathlib import Path

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEIGHTS_ROOT = PROJECT_ROOT / "weights"

DEFAULT_SOM_MODEL_PATH = WEIGHTS_ROOT / "icon_detect" / "model.pt"
DEFAULT_CAPTION_MODEL_PATH = WEIGHTS_ROOT / "icon_caption_florence"


class Settings:
    app_name = "Omniparser_AutoUI"
    app_version = "0.1.0"
    default_model = "omniparser-autoui"
    caption_model_name = "florence2"
    box_threshold = 0.05
    requested_device = os.getenv("OMNIPARSER_DEVICE", "cuda")
    device = (
        "cuda"
        if requested_device == "cuda" and torch.cuda.is_available()
        else "cpu"
    )
    som_model_path = DEFAULT_SOM_MODEL_PATH
    caption_model_path = DEFAULT_CAPTION_MODEL_PATH
