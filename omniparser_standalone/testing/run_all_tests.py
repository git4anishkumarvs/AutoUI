from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from common import ASSETS, OUTPUT, elapsed_seconds, list_images, now

ROOT = Path(__file__).resolve().parent
TEST_SCRIPTS = [
    "test_find_controls.py",
    "test_ground_controls.py",
    "test_openai_like.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all Omniparser_AutoUI API tests for every image in assets")
    parser.add_argument("--python", default=sys.executable, help="Python executable to use for child scripts")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010", help="Running API base URL")
    parser.add_argument("--assets-dir", type=Path, default=ASSETS, help="Folder containing input images")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT, help="Root output folder; JSON goes to output/json and images go to output/images")
    parser.add_argument("--skip-openai", action="store_true", help="Skip the OpenAI-like endpoint test")
    return parser.parse_args()


def run_script(python_exe: str, script_name: str, base_url: str, image: Path, output_dir: Path) -> None:
    cmd = [python_exe, script_name, "--base-url", base_url, "--image", str(image), "--output-dir", str(output_dir)]
    print(f"\n=== Running {script_name} for {image.name} ===")
    started_at = now()
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    print({"script": script_name, "image": image.name, "elapsed_seconds": elapsed_seconds(started_at)})


if __name__ == "__main__":
    args = parse_args()
    batch_started_at = now()
    images = list_images(args.assets_dir)
    if not images:
        raise SystemExit(f"No images found in {args.assets_dir}")

    health_cmd = [args.python, "test_health.py", "--base-url", args.base_url]
    print("\n=== Running test_health.py ===")
    health_started_at = now()
    health_result = subprocess.run(health_cmd, cwd=ROOT)
    if health_result.returncode != 0:
        raise SystemExit(health_result.returncode)
    print({"script": "test_health.py", "elapsed_seconds": elapsed_seconds(health_started_at)})

    scripts = TEST_SCRIPTS if not args.skip_openai else TEST_SCRIPTS[:-1]
    for image in images:
        for script_name in scripts:
            run_script(args.python, script_name, args.base_url, image, args.output_dir)
    print(
        f"\nAll tests completed successfully for {len(images)} image(s). "
        f"JSON: {args.output_dir / 'json'} Images: {args.output_dir / 'images'} "
        f"Total elapsed_seconds: {elapsed_seconds(batch_started_at)}"
    )
