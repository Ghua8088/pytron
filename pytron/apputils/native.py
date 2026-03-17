import sys
import os
from typing import Optional

from pytron.utils import resolve_os_module

pytron_os = resolve_os_module()


class NativeMixin:
    """
    Mixin class to handle native system interactions.
    """

    def set_start_on_boot(self, enable=True):
        """
        Enables or disables automatic application startup on system boot.
        """
        app_name = self.config.get("title", "PytronApp")
        # Sanitize for registry key/filename
        safe_name = "".join(c if c.isalnum() else "_" for c in app_name)

        if not getattr(sys, "frozen", False):
            self.logger.info("Skipping Start-on-Boot registration in Development Mode.")
            return False

        # Attempt native Rust implementation first for performance
        try:
            if pytron_os is not None:
                exe_path = sys.executable
                if pytron_os.set_launch_on_boot(safe_name, exe_path, enable):
                    return True
        except Exception:
            pass

        # Fallback to platform-specific Python implementations
        try:
            sys_plat = sys.platform
            exe_path = f'"{sys.executable}"'

            impl = None
            if sys_plat == "win32":
                from ..platforms.windows import WindowsImplementation

                impl = WindowsImplementation()
            elif sys_plat == "linux":
                from ..platforms.linux import LinuxImplementation

                impl = LinuxImplementation()
            elif sys_plat == "darwin":
                from ..platforms.darwin import DarwinImplementation

                impl = DarwinImplementation()

            if impl:
                return impl.set_launch_on_boot(safe_name, exe_path, enable)
        except Exception as e:
            self.logger.warning(f"Could not set start on boot during fallback: {e}")

        return False

    def message_box(self, title, message, style=0):
        """
        Shows a native message box.
        Styles: 0=OK, 1=OK/Cancel, 2=Abort/Retry/Ignore, 3=Yes/No/Cancel, 4=Yes/No, 5=Retry/Cancel
        Returns: 1=OK, 2=Cancel, 6=Yes, 7=No
        """
        if self.windows:
            return self.windows[0].message_box(title, message, style)
        return 0

    def dialog_save_file(
        self, title="Save File", default_path=None, default_name=None, file_types=None
    ):
        """Opens a native save file dialog. Returns the selected path or None."""
        if self.windows:
            return self.windows[0].dialog_save_file(
                title, default_path, default_name, file_types
            )
        return None

    def dialog_open_file(self, title="Open File", default_path=None, file_types=None):
        """Opens a native file selection dialog. Returns the selected path or None."""
        if self.windows:
            return self.windows[0].dialog_open_file(title, default_path, file_types)
        return None

    def dialog_open_folder(self, title="Select Folder", default_path=None):
        """Opens a native folder selection dialog. Returns the selected path or None."""
        if self.windows:
            return self.windows[0].dialog_open_folder(title, default_path)
        return None

    def system_notification(self, title: Optional[str] = None, message: str = ""):
        """Sends a system-level (tray/toast) notification via the OS."""
        if not title:
            title = self.config.get("author", self.config.get("title", "Pytron"))

        icon = self.config.get("icon")

        if self.windows:
            for window in self.windows:
                try:
                    window.system_notification(title, message, icon=icon)
                    break
                except Exception as e:
                    self.logger.debug(
                        f"Failed to send notification via window {window}: {e}"
                    )

    def show_toast(self, config: dict):
        """
        Sends a rich, modern system notification.
        Example config:
        {
            "title": "Hello",
            "body": "World",
            "image": "path/to/hero.jpg",
            "icon": "path/to/icon.png",
            "actions": [{"label": "Open", "action": "pytron://open"}]
        }
        """
        if self.windows:
            for window in self.windows:
                try:
                    window.toast(config)
                    break
                except Exception as e:
                    self.logger.debug(f"Failed to send toast via window {window}: {e}")

    def copy_to_clipboard(self, text: str):
        """Copies text to the system clipboard."""
        if self.windows:
            return self.windows[0]._platform.set_clipboard_text(text)
        return False

    def get_clipboard_text(self):
        """Returns text from the system clipboard."""
        if self.windows:
            return self.windows[0]._platform.get_clipboard_text()
        return None

    def get_system_info(self):
        """Returns hardware and OS information."""
        if self.windows:
            return self.windows[0]._platform.get_system_info()

        # Fallback if no window
        import os

        arch = "unknown"
        if sys.platform == "win32":
            arch = os.environ.get("PROCESSOR_ARCHITECTURE", "unknown")
        else:
            try:
                arch = os.uname().machine
            except:
                pass

        return {"os": sys.platform, "arch": arch}

    def store_set(self, key: str, value):
        """Persists a value to the app's local storage."""
        # Fix recursion: This was incorrectly calling self.store_set instead of the ConfigMixin implementation
        if hasattr(super(), "store_set"):
            return super().store_set(key, value)
        return False

    def store_get(self, key: str, default=None):
        """Retrieves a persisted value from the app's local storage."""
        if hasattr(super(), "store_get"):
            return super().store_get(key, default)
        return default

    def store_delete(self, key: str):
        """Removes a persisted value."""
        if hasattr(super(), "store_delete"):
            return super().store_delete(key)
        return False
