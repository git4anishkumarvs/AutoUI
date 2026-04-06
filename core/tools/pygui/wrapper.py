import subprocess
import time
import os
import ctypes
import ctypes.wintypes

from core.common.automation_wrapper import BaseAutomationWrapper
from core.common.vlm_interaction import execute_vlm_interaction


def _get_window_rect_by_hwnd(hwnd):
    """Returns (left, top, right, bottom) of a window by its HWND handle."""
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def find_hwnd_for_exe(exe_name: str) -> tuple:
    """
    Enumerate all visible top-level windows and find the first one whose
    title matches known aliases for the given executable.
    Returns (hwnd, title) or (None, None).
    """
    search_terms = [os.path.splitext(exe_name)[0].lower()]
    if "calc" in exe_name.lower():
        search_terms.append("calculator")
    if "mspaint" in exe_name.lower():
        search_terms.append("mspaint")

    found = []

    def callback(hwnd, lParam):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value.strip()
            if title:
                for term in search_terms:
                    if term in title.lower():
                        found.append((hwnd, title))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    ctypes.windll.user32.EnumWindows(WNDENUMPROC(callback), 0)
    return (found[0][0], found[0][1]) if found else (None, None)


class PyGUIWrapper(BaseAutomationWrapper):
    """
    PyGUI automation wrapper.
    Responsible for:
      - Native Win32 process launch and window HWND tracking.
      - Capturing the precise window region screenshot (Step 1).
      - Delegating Steps 2-8 (VLM comms + action execution) to core.common.vlm_interaction.
    """
    def __init__(self):
        self.process = None
        self._target_hwnd = None
        self._target_title = None

    def launch(self, app_path: str):
        print(f"[PyGUIWrapper] Launching process: {app_path}")
        self.process = subprocess.Popen([app_path])
        time.sleep(2)  # Wait for UI to fully render before tracking
        exe_name = os.path.basename(app_path)
        hwnd, title = find_hwnd_for_exe(exe_name)
        if hwnd:
            self._target_hwnd = hwnd
            self._target_title = title
            print(f"[PyGUIWrapper] [OK] Window resolved on launch: '{title}' (hwnd={hwnd})")
        return self.process

    def focus_window(self):
        """Raises the tracked window to foreground."""
        if self._target_hwnd:
            ctypes.windll.user32.ShowWindow(self._target_hwnd, 9)   # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(self._target_hwnd)
            time.sleep(0.8)
            print(f"[PyGUIWrapper] [FOCUSED] '{self._target_title}'")
            return True
        print("[PyGUIWrapper] [WARNING] No tracked window HWND -- cannot focus.")
        return False

    def terminate(self):
        if self.process:
            print("[PyGUIWrapper] Terminating process.")
            try:
                self.process.kill()
            except Exception:
                pass
            if hasattr(self.process, 'args') and self.process.args:
                try:
                    exe_name = os.path.basename(self.process.args[0])
                    if exe_name.lower() == "calc.exe":
                        subprocess.call(['taskkill', '/F', '/IM', 'CalculatorApp.exe'],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.call(['taskkill', '/F', '/IM', exe_name],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            self.process = None
            self._target_hwnd = None

    def click(self, locator: str, locator_type: str = "default"):
        print(f"[PyGUIWrapper] [CLICK] '{locator}' (strategy='{locator_type}')")
        if locator_type.lower() == "vlm":
            self._execute_vlm_interaction(locator, action="click")

    def type_text(self, locator: str, text: str, locator_type: str = "default"):
        print(f"[PyGUIWrapper] [TYPE] '{text}' into: '{locator}' (strategy='{locator_type}')")
        if locator_type.lower() == "vlm":
            self._execute_vlm_interaction(locator, action="type", text=text)

    def _execute_vlm_interaction(self, query: str, action: str, text: str = None):
        """
        Step 1: Capture the window screenshot using HWND bounds.
        Steps 2-8: Delegated to core.common.vlm_interaction.execute_vlm_interaction.
        """
        try:
            import pyautogui

            # -- Step 1: Capture exact target window region via HWND ----------
            if self._target_hwnd:
                left, top, right, bottom = _get_window_rect_by_hwnd(self._target_hwnd)
                width = right - left
                height = bottom - top
                if width <= 0 or height <= 0:
                    raise ValueError(
                        f"Window '{self._target_title}' has invalid bounds: {left},{top},{right},{bottom}"
                    )
                print(f"[Step 1] Capturing window '{self._target_title}' region: "
                      f"left={left}, top={top}, width={width}, height={height}")
                screenshot = pyautogui.screenshot(region=(left, top, width, height))
                win_left, win_top = left, top
            else:
                print("[Step 1] No HWND tracked -- falling back to full screen capture.")
                screenshot = pyautogui.screenshot()
                win_left, win_top = 0, 0

            # -- Steps 2-8: Handled by common VLM interaction pipeline --------
            return execute_vlm_interaction(
                screenshot=screenshot,
                win_left=win_left,
                win_top=win_top,
                query=query,
                action=action,
                text=text,
                target_hwnd=self._target_hwnd,
                target_title=self._target_title,
            )

        except Exception as e:
            print(f"[PyGUIWrapper] CRITICAL pipeline failure: {e}")
            raise RuntimeError(f"VLM interaction failed for '{query}' during '{action}': {e}") from e

    def scroll(self, direction: str):
        print(f"[PyGUIWrapper] [SCROLL] {direction}")
