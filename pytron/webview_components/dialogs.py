import os
from typing import Any, Optional, List, Tuple
from .base import WebviewComponent


class DialogComponent(WebviewComponent):
    """Handles system dialogs, notifications, and taskbar status."""

    def open_file(self, *args, **kwargs) -> List[str]:
        """Opens a native file selection dialog."""
        # 1. Prioritize Platform Implementation (pytron_native / System Hooks)
        if self.webview._platform and self.webview.hwnd:
            title = kwargs.get("title") or (args[0] if args else "Open File")
            default_path = kwargs.get("default_path") or (
                args[1] if len(args) > 1 else None
            )
            file_types = kwargs.get("file_types") or (
                args[2] if len(args) > 2 else None
            )
            return self.webview._platform.open_file_dialog(
                self.webview.hwnd, title, default_path, file_types
            )

        # 2. Fallback to Engine Bridge (Renderer-specific dialogs)
        if hasattr(self.native, "dialog_open_file"):
            title = kwargs.get("title") or (args[0] if args else "Open File")
            default_path = kwargs.get("default_path") or (
                args[1] if len(args) > 1 else None
            )
            file_types = kwargs.get("file_types") or (
                args[2] if len(args) > 2 else None
            )

            filters_str = None
            if file_types:
                parts = []
                for name_ft, pat in file_types:
                    exts = pat.replace("*.", "").replace(";", ",")
                    parts.append(f"{name_ft}:{exts}")
                filters_str = ";".join(parts)
            return self.native.dialog_open_file(title, default_path, filters_str)

        return []

    def save_file(self, *args, **kwargs) -> Optional[str]:
        """Opens a native file save dialog."""
        # 1. Prioritize Platform Implementation
        if self.webview._platform and self.webview.hwnd:
            title = kwargs.get("title", "Save File")
            default_path = kwargs.get("default_path")
            default_name = kwargs.get("default_name")
            file_types = kwargs.get("file_types")
            return self.webview._platform.save_file_dialog(
                self.webview.hwnd, title, default_path, default_name, file_types
            )

        # 2. Fallback to Engine Bridge
        if hasattr(self.native, "dialog_save_file"):
            title = kwargs.get("title", "Save File")
            default_path = kwargs.get("default_path")
            default_name = kwargs.get("default_name")
            file_types = kwargs.get("file_types")
            filters_str = None
            if file_types:
                parts = []
                for name, pat in file_types:
                    exts = pat.replace("*.", "").replace(";", ",")
                    parts.append(f"{name}:{exts}")
                filters_str = ";".join(parts)
            return self.native.dialog_save_file(
                title, default_path, default_name, filters_str
            )

        return None

    def open_folder(self, *args, **kwargs) -> Optional[str]:
        """Opens a native folder selection dialog."""
        # 1. Prioritize Platform Implementation
        if self.webview._platform and self.webview.hwnd:
            title = kwargs.get("title", "Select Folder")
            default_path = kwargs.get("default_path")
            return self.webview._platform.open_folder_dialog(
                self.webview.hwnd, title, default_path
            )

        # 2. Fallback to Engine Bridge
        if hasattr(self.native, "dialog_open_folder"):
            title = kwargs.get("title", "Select Folder")
            default_path = kwargs.get("default_path")
            return self.native.dialog_open_folder(title, default_path)

        return None

    def message_box(self, *args, **kwargs) -> int:
        """Displays a native system message box."""
        if self.webview._platform and self.webview.hwnd:
            return self.webview._platform.message_box(
                self.webview.hwnd, *args, **kwargs
            )
        return 0

    def set_taskbar_progress(
        self, state: str = "normal", value: int = 0, max_value: int = 100
    ):
        """Updates the application icon progress bar in the system taskbar."""
        # 1. Prioritize Platform Implementation (Centralized pytron_native hook)
        if self.webview._platform and self.webview.hwnd:
            self.webview._platform.set_taskbar_progress(
                self.webview.hwnd, state, value, max_value
            )
            return

        # 2. Fallback to Engine Bridge (if the shell implements its own taskbar logic)
        if hasattr(self.native, "set_taskbar_progress"):
            s_map = {
                "normal": 2,
                "error": 4,
                "paused": 8,
                "indeterminate": 1,
                "none": 0,
            }
            s_code = s_map.get(state, 0)
            self.native.set_taskbar_progress(s_code, int(value), int(max_value))

    def notification(self, title: str, message: str, icon: Optional[str] = None):
        """Displays a system tray notification."""
        if self.webview._platform and self.webview.hwnd:
            if not icon:
                icon = self.webview.config.get("icon")
            self.webview._platform.notification(self.webview.hwnd, title, message, icon)

    def toast(self, config: dict):
        """Displays a modern toast notification (Platform-specific)."""
        if self.webview._platform and self.webview.hwnd:
            if "app_id" not in config:
                config["app_id"] = self.webview.config.get("title", "Pytron")
            if "icon" not in config:
                config["icon"] = self.webview.config.get("icon")

            # Resolve paths for images
            root_path = self.webview._routing_comp.root_path
            app_root = self.webview._app_root
            for key in ["image", "icon", "inline_image"]:
                path = config.get(key)
                if path and not os.path.isabs(path):
                    possible_path = os.path.join(root_path, path)
                    if os.path.exists(possible_path):
                        config[key] = possible_path
                    else:
                        possible_path = os.path.join(str(app_root), path)
                        if os.path.exists(possible_path):
                            config[key] = possible_path

            self.webview._platform.toast(self.webview.hwnd, config)
