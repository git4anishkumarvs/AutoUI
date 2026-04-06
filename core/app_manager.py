import os
from core.tools.pygui.wrapper import PyGUIWrapper

class AppManager:
    def __init__(self, config):
        """
        Initialize the App Manager with a loaded configparser configuration.
        """
        self.config = config
        self.active_apps = {}  # Map of app_alias -> Wrapper instance
        
        # Determine the backend tool from config
        self.automation_tool = self.config.get("Automation", "tool", fallback="PyGUITest")

    def get_wrapper(self):
        """
        Factory method to return the correct wrapper based on configured automation tool.
        Future support: PlaywrightWrapper, SeleniumWrapper, etc.
        """
        if self.automation_tool.lower() == "pyguitest":
            return PyGUIWrapper()
        # Default fallback
        return PyGUIWrapper()

    def launch_app(self, app_alias, app_path=None):
        """
        Launches an application natively using the configured dynamic Wrapper.
        """
        if not app_path:
            if not self.config.has_section(app_alias):
                raise ValueError(f"Application alias '{app_alias}' not found in configuration.")
            app_path = self.config.get(app_alias, "path")
            
        print(f"[AppManager] Launching '{app_alias}' using {self.automation_tool} -> {app_path}")
        
        # Instantiate the correct wrapper dynamically
        wrapper = self.get_wrapper()
        wrapper.launch(app_path)
        
        self.active_apps[app_alias] = wrapper
        return wrapper

    def switch_to_app(self, app_alias):
        import time, os
        
        if app_alias not in self.active_apps:
            print(f"[AppManager] App '{app_alias}' is not currently running. Launching first.")
            self.launch_app(app_alias)
        
        wrapper = self.active_apps[app_alias]
        print(f"[AppManager] Switching context to '{app_alias}'")
        
        # Refresh HWND in case the process spawned a different window after launch
        # (e.g. calc.exe → Calculator UWP window)
        try:
            from core.tools.pygui.wrapper import find_hwnd_for_exe
            proc = wrapper.process
            exe_name = "unknown.exe"
            if proc and hasattr(proc, 'args') and proc.args:
                exe_name = os.path.basename(proc.args[0])
            
            hwnd, title = find_hwnd_for_exe(exe_name)
            if hwnd:
                wrapper._target_hwnd = hwnd
                wrapper._target_title = title
                print(f"[AppManager] 🔄 HWND refreshed: '{title}' (hwnd={hwnd})")
        except Exception as e:
            print(f"[AppManager] HWND refresh skipped: {e}")
        
        # Delegate to wrapper to physically raise the window
        wrapper.focus_window()



    # Generic UI Interaction Abstractions exposed to BDD framework
    def interact_click(self, app_alias, locator, locator_type="default"):
        if app_alias in self.active_apps:
            self.active_apps[app_alias].click(locator, locator_type)
            
    def interact_type(self, app_alias, locator, text, locator_type="default"):
        if app_alias in self.active_apps:
            self.active_apps[app_alias].type_text(locator, text, locator_type)

    def interact_scroll(self, app_alias, direction):
        if app_alias in self.active_apps:
            self.active_apps[app_alias].scroll(direction)

    def terminate_all(self):
        """
        Closes all launched applications.
        """
        for alias, wrapper in self.active_apps.items():
            print(f"[AppManager] Terminating '{alias}'")
            try:
                wrapper.terminate()
            except Exception as e:
                print(f"[AppManager] Error terminating '{alias}': {e}")
        self.active_apps.clear()
