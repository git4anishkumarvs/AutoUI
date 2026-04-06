from __future__ import annotations

import argparse

import requests

from common import elapsed_seconds, now


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Health check for Omniparser_AutoUI")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    started_at = now()
    response = requests.get(f"{args.base_url}/health", timeout=30)
    response.raise_for_status()
    print({"response": response.json(), "elapsed_seconds": elapsed_seconds(started_at)})
