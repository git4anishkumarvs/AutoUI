from __future__ import annotations

import argparse
from pathlib import Path

import requests

from common import DEFAULT_BASE_URL, DEFAULT_IMAGE, JSON_OUTPUT, elapsed_seconds, image_to_base64, now, save_json, stemmed_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test /api/v1/find-controls")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--json-dir", type=Path, default=JSON_OUTPUT)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    json_dir = args.json_dir if args.output_dir is None else args.output_dir / "json"
    out_path = args.out or stemmed_path(json_dir, args.image, "_find_controls.json")
    payload = {"image_base64": image_to_base64(args.image)}
    started_at = now()
    response = requests.post(f"{args.base_url}/api/v1/find-controls", json=payload, timeout=300)
    if not response.ok:
        print({"status_code": response.status_code, "body": response.text, "image": str(args.image)})
        response.raise_for_status()
    data = response.json()
    save_json(data, out_path)
    print(
        {
            "saved": str(out_path),
            "device": data.get("device"),
            "control_count": data.get("control_count"),
            "image": str(args.image),
            "elapsed_seconds": elapsed_seconds(started_at),
            "server_latency_seconds": data.get("latency_seconds"),
        }
    )
