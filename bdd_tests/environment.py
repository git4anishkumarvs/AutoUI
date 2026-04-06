import logging
import os
import sys
import requests

# Add the project root to sys.path so we can import 'core' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.common.config_parser import load_config
from core.app_manager import AppManager
from core.common.vlm_config import build_vlm_url

def scenario_uses_vlm(scenario):
    for step in getattr(scenario, "steps", []):
        if 'identified by "vlm"' in step.name.lower():
            return True
    return False

def ensure_vlm_ready():
    status_url = build_vlm_url("/status")
    warmup_url = build_vlm_url("/warmup")

    try:
        status_response = requests.get(status_url, timeout=3)
        status_response.raise_for_status()
    except Exception as e:
        raise RuntimeError(
            f"VLM service is not reachable at {status_url}. "
            "Start or restart the FastAPI vision service before running VLM scenarios."
        ) from e

    try:
        warmup_response = requests.get(warmup_url, timeout=30)
    except Exception as e:
        raise RuntimeError(
            "VLM service is reachable, but warmup failed to execute. "
            "Restart the vision service and try again."
        ) from e

    if warmup_response.status_code == 404:
        raise RuntimeError(
            "The running VLM service is using stale code and does not expose /warmup. "
            "Restart the FastAPI vision service so it loads the latest code changes."
        )

    if warmup_response.status_code >= 400:
        detail = warmup_response.text
        try:
            detail = warmup_response.json().get("detail", detail)
        except Exception:
            pass
        raise RuntimeError(f"VLM backend warmup failed: {detail}")

def before_all(context):
    print("Setting up global environment.")
    # Initialize logging or other global settings
    logging.basicConfig(level=logging.INFO)
    
    # Load configuration and initialize App Manager global instance
    context.config_data = load_config("config.ini")
    context.app_manager = AppManager(context.config_data)

def after_all(context):
    print("Tearing down global environment (Skipping auto-app termination).")
    # Apps will now only be closed if explicitly requested in a feature file.
    pass

def before_feature(context, feature):
    print(f"\nStarting feature: {feature.name}")

def after_feature(context, feature):
    print(f"Finished feature: {feature.name}")

def before_scenario(context, scenario):
    print(f"  Starting scenario: {scenario.name}")
    # Initialize driver/session here if testing web UI
    context.driver = None

    if scenario_uses_vlm(scenario):
        print("  Verifying VLM service readiness for this scenario...")
        ensure_vlm_ready()

def after_scenario(context, scenario):
    print(f"  Finished scenario: {scenario.name} (Status: {scenario.status})")
    if scenario.status == "failed":
        print(f"    [!] Scenario failed. Capture screenshot or logs here.")
    # Quit driver/session here if testing web UI
