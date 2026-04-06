from __future__ import annotations

import argparse
import base64
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "output"
JSON_OUTPUT = OUTPUT / "json"
IMAGE_OUTPUT = OUTPUT / "images"
DEFAULT_IMAGE = ASSETS / "sample_ui.png"
DEFAULT_BASE_URL = "http://127.0.0.1:8010"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def image_to_base64(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode("ascii")


def save_json(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def ensure_output_dir(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def stemmed_path(output_dir: Path, image_path: Path, suffix: str) -> Path:
    return ensure_output_dir(output_dir) / f"{image_path.stem}{suffix}"


def list_images(assets_dir: Path) -> list[Path]:
    return sorted(
        [path for path in assets_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS]
    )


def now() -> float:
    return time.perf_counter()


def elapsed_seconds(start: float) -> float:
    return round(time.perf_counter() - start, 4)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shared helpers are imported by test scripts.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--assets-dir", type=Path, default=ASSETS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print({"base_url": args.base_url, "image": str(args.image), "assets_dir": str(args.assets_dir), "output_dir": str(args.output_dir)})
