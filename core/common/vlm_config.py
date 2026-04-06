import json
import os
from urllib.parse import urlparse


def _config_path():
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "vlm_service", "config.json")
    )


def load_vlm_config():
    with open(_config_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def get_active_backend(config=None):
    config = config or load_vlm_config()
    return config.get("backend", "huggingface")


def get_vlm_service_url(config=None):
    config = config or load_vlm_config()
    backend = get_active_backend(config)
    backend_config = config.get(backend, {})
    base_url = (
        backend_config.get("service_url")
        or config.get("service", {}).get("base_url")
        or "http://127.0.0.1:8000"
    )
    return base_url.rstrip("/")


def build_vlm_url(path, config=None):
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{get_vlm_service_url(config)}{path}"


def get_local_service_binding(config=None):
    parsed = urlparse(get_vlm_service_url(config))
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, port
