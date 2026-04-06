from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare CPU and GPU benchmark JSON outputs.")
    parser.add_argument("--cpu-dir", type=Path, required=True, help="JSON output directory from the CPU run")
    parser.add_argument("--gpu-dir", type=Path, required=True, help="JSON output directory from the GPU run")
    return parser.parse_args()


def load_metrics(json_dir: Path) -> dict[str, dict[str, float | str | None]]:
    metrics = {}
    for path in sorted(json_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        metrics[path.name] = {
            "latency_seconds": data.get("latency_seconds"),
            "device": data.get("device"),
            "control_count": data.get("control_count"),
        }
    return metrics


def ensure_directory_exists(json_dir: Path, label: str) -> None:
    if not json_dir.exists():
        raise SystemExit(f"{label} directory does not exist: {json_dir}")
    if not json_dir.is_dir():
        raise SystemExit(f"{label} path is not a directory: {json_dir}")


def safe_speedup(cpu_latency: float | None, gpu_latency: float | None) -> float | None:
    if not cpu_latency or not gpu_latency:
        return None
    if gpu_latency == 0:
        return None
    return round(cpu_latency / gpu_latency, 4)


def summarize(metrics: dict[str, dict[str, float | str | None]]) -> dict[str, float | int]:
    grouped = defaultdict(list)
    for filename, values in metrics.items():
        if filename.endswith("_find_controls.json"):
            grouped["find_controls"].append(values.get("latency_seconds"))
        elif filename.endswith("_ground_controls.json"):
            grouped["ground_controls"].append(values.get("latency_seconds"))
        elif filename.endswith("_responses.json"):
            grouped["responses"].append(values.get("latency_seconds"))

    summary = {}
    for key, values in grouped.items():
        numeric = [value for value in values if isinstance(value, (int, float))]
        if numeric:
            summary[f"{key}_avg_seconds"] = round(sum(numeric) / len(numeric), 4)
            summary[f"{key}_count"] = len(numeric)
    return summary


if __name__ == "__main__":
    args = parse_args()
    ensure_directory_exists(args.cpu_dir, "CPU")
    ensure_directory_exists(args.gpu_dir, "GPU")
    cpu_metrics = load_metrics(args.cpu_dir)
    gpu_metrics = load_metrics(args.gpu_dir)

    if not cpu_metrics:
        raise SystemExit(f"No JSON files were found in the CPU directory: {args.cpu_dir}")
    if not gpu_metrics:
        raise SystemExit(f"No JSON files were found in the GPU directory: {args.gpu_dir}")

    common_files = sorted(set(cpu_metrics) & set(gpu_metrics))
    if not common_files:
        raise SystemExit(
            "No matching JSON files were found between the CPU and GPU directories.\n"
            f"CPU files: {', '.join(sorted(cpu_metrics))}\n"
            f"GPU files: {', '.join(sorted(gpu_metrics))}"
        )

    print("\nPer-file comparison:")
    for filename in common_files:
        cpu_entry = cpu_metrics[filename]
        gpu_entry = gpu_metrics[filename]
        print(
            {
                "file": filename,
                "cpu_device": cpu_entry.get("device"),
                "cpu_latency_seconds": cpu_entry.get("latency_seconds"),
                "gpu_device": gpu_entry.get("device"),
                "gpu_latency_seconds": gpu_entry.get("latency_seconds"),
                "speedup_x": safe_speedup(cpu_entry.get("latency_seconds"), gpu_entry.get("latency_seconds")),
            }
        )

    cpu_summary = summarize(cpu_metrics)
    gpu_summary = summarize(gpu_metrics)
    print("\nSummary:")
    print({"cpu": cpu_summary, "gpu": gpu_summary})

    for prefix in ("find_controls", "ground_controls", "responses"):
        cpu_avg = cpu_summary.get(f"{prefix}_avg_seconds")
        gpu_avg = gpu_summary.get(f"{prefix}_avg_seconds")
        if isinstance(cpu_avg, (int, float)) and isinstance(gpu_avg, (int, float)):
            print(
                {
                    "benchmark": prefix,
                    "cpu_avg_seconds": cpu_avg,
                    "gpu_avg_seconds": gpu_avg,
                    "speedup_x": safe_speedup(cpu_avg, gpu_avg),
                }
            )
