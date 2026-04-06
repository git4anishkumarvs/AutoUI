from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test vlm_service /find_controls with an image.")
    parser.add_argument("--image", type=Path, required=True, help="Path to the input screenshot/image.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for the running vlm_service.")
    parser.add_argument(
        "--grounded",
        action="store_true",
        help="Request grounded_image_base64 output from the backend.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to save the raw JSON response.",
    )
    parser.add_argument(
        "--grounded-out",
        type=Path,
        default=None,
        help="Optional path to save the grounded image when --grounded is used.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Request timeout in seconds.",
    )
    return parser.parse_args()


def save_json(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_grounded_image(data: dict, output_path: Path) -> bool:
    grounded_image = data.get("grounded_image_base64")
    if not grounded_image:
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(grounded_image))
    return True


def print_summary(data: dict) -> None:
    controls = data.get("controls", [])
    print(f"model={data.get('model')}")
    print(f"device={data.get('device')}")
    print(f"image_size={data.get('image_width')}x{data.get('image_height')}")
    print(f"control_count={data.get('control_count')}")
    print(f"latency_seconds={data.get('latency_seconds')}")
    print("")
    for control in controls:
        bbox = control.get("bbox", {})
        center = control.get("center", {})
        print(
            f"[{control.get('id')}] "
            f"type={control.get('type')} "
            f"interactive={control.get('interactivity')} "
            f"content={repr(control.get('content'))} "
            f"center=({center.get('x')}, {center.get('y')}) "
            f"bbox=({bbox.get('x1')}, {bbox.get('y1')}, {bbox.get('x2')}, {bbox.get('y2')})"
        )


def main() -> int:
    args = parse_args()

    if not args.image.exists():
        raise FileNotFoundError(f"Image not found: {args.image}")

    endpoint = "/ground_controls" if args.grounded else "/find_controls"
    with args.image.open("rb") as handle:
        response = requests.post(
            f"{args.base_url.rstrip('/')}{endpoint}",
            files={"screenshot": (args.image.name, handle, "image/png")},
            data={"include_grounded_image": "true"} if args.grounded else {},
            timeout=args.timeout,
        )

    if not response.ok:
        print(response.text)
        response.raise_for_status()

    data = response.json()
    print_summary(data)

    if args.json_out:
        save_json(data, args.json_out)
        print(f"\nSaved JSON to: {args.json_out}")

    if args.grounded_out:
        if save_grounded_image(data, args.grounded_out):
            print(f"Saved grounded image to: {args.grounded_out}")
        else:
            print("Grounded image was not present in the response.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
