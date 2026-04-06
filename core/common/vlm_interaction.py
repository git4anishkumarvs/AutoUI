"""
core/common/vlm_interaction.py
================================
Generic VLM interaction pipeline usable by any automation tool wrapper.

Any tool (PyGUI, Playwright, Selenium, UIA) can:
  1. Capture a screenshot however it likes (viewport, window region, full screen).
  2. Call execute_vlm_interaction() with that screenshot + window origin.
  3. Receive click/type actions executed at the correct absolute screen coordinates.
"""

import time
import io
import os
import ctypes
from datetime import datetime

from core.common.vlm_config import build_vlm_url


def _sanitize_filename(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value.strip())
    return cleaned[:80] or "unnamed"


def save_debug_screenshot(image, query: str, action: str) -> str:
    """Save a PIL screenshot to debug_artifacts/screenshots/ and return the path."""
    screenshots_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "debug_artifacts", "screenshots")
    )
    os.makedirs(screenshots_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}_{action}_{_sanitize_filename(query)}.png"
    filepath = os.path.join(screenshots_dir, filename)
    image.save(filepath, format="PNG")
    print(f"[Step 1] Screenshot saved to: {filepath}")
    return filepath


def build_proxy_curl_command(query: str, action: str, screenshot_path: str) -> str:
    """Build a representative cURL command for debug logging."""
    return (
        f'curl -X POST "{build_vlm_url("/find_control")}" '
        f'-F "query={query}" '
        f'-F "action_type={action}" '
        f'-F "screenshot=@{screenshot_path};type=image/png"'
    )


def execute_vlm_interaction(
    screenshot,
    win_left: int,
    win_top: int,
    query: str,
    action: str,
    text: str = None,
    target_hwnd=None,
    target_title: str = "",
):
    """
    Steps 2–8 of the VLM interaction pipeline.
    ============================================
    Caller is responsible for Step 1 (capturing the screenshot and providing
    win_left/win_top offsets relative to the screen origin).

    Args:
        screenshot:   PIL.Image — the captured window/screen region.
        win_left:     X offset of the captured region on the physical screen.
        win_top:      Y offset of the captured region on the physical screen.
        query:        Natural-language description of the UI element.
        action:       "click" or "type".
        text:         Text to type (only needed when action == "type").
        target_hwnd:  Win32 HWND handle to re-focus before acting (optional).
        target_title: Human-readable window title for log messages.

    Returns:
        dict with keys: status, target_x, target_y, query, action.

    Raises:
        RuntimeError on any failure.
    """
    import requests
    import pyautogui

    screenshot_path = save_debug_screenshot(screenshot, query, action)

    # -- Step 2: Serialize screenshot to PNG bytes (no resizing) --------------
    orig_width, orig_height = screenshot.size
    print(f"[Step 2] Processing native screenshot resolution: {orig_width}x{orig_height}")
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    # -- Step 3: POST screenshot + query to VLM API ---------------------------
    print(f"[Step 3] Sending query '{query}' to VLM API (action='{action}')...")
    print(f"[Step 3] curl => {build_proxy_curl_command(query, action, screenshot_path)}")
    try:
        response = requests.post(
            build_vlm_url("/find_control"),
            data={"query": query, "action_type": action},
            files={"screenshot": ("screen.png", img_bytes, "image/png")},
            timeout=120,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        detail = ""
        if e.response is not None:
            try:
                detail = e.response.json().get("detail", e.response.text)
            except Exception:
                detail = e.response.text
        message = (
            f"VLM API request failed while trying to {action} '{query}'. "
            f"HTTP {e.response.status_code if e.response is not None else 'unknown'}"
        )
        if detail:
            message += f": {detail}"
        raise RuntimeError(message) from e

    data = response.json()

    if data.get("status") != "success":
        raise RuntimeError(
            f"VLM could not locate element '{query}'. "
            f"Reason: {data.get('reason', 'Unknown reason')}. "
            f"Raw response: {str(data.get('raw_response', 'N/A'))[:200]}"
        )

    # -- Step 4: Receive VLM coordinates --------------------------------------
    coords = data["coordinates"]
    print(f"[Step 4] VLM returned screenshot-space coordinates: x={coords['x']}, y={coords['y']}")

    # -- Step 5: Coordinates are already in native window-pixel space ---------
    local_x, local_y = coords["x"], coords["y"]
    print(f"[Step 5] Native window-relative pixels (no scaling): x={int(local_x)}, y={int(local_y)}")

    # -- Step 6: Translate to absolute screen coordinates ---------------------
    target_x = win_left + int(local_x)
    target_y = win_top + int(local_y)
    print(f"[Step 6] Absolute screen coords: x={target_x}, y={target_y}  "
          f"(window_origin={win_left},{win_top})")

    # -- Step 7: Re-focus the target window before acting ---------------------
    if target_hwnd:
        print(f"[Step 7] Re-focusing '{target_title}' before action...")
        ctypes.windll.user32.SetForegroundWindow(target_hwnd)
        time.sleep(0.3)

    # -- Step 8: Execute physical action at resolved coordinates --------------
    print(f"[Step 8] Executing '{action}' at screen position ({target_x}, {target_y})")
    if action == "click":
        pyautogui.click(x=target_x, y=target_y)
    elif action == "type":
        import pyperclip
        pyautogui.click(x=target_x, y=target_y)
        time.sleep(0.1)
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")

    print(f"[Step 8] DONE -- '{action}' completed successfully at ({target_x}, {target_y})")
    return {
        "status": "success",
        "target_x": target_x,
        "target_y": target_y,
        "query": query,
        "action": action,
    }
