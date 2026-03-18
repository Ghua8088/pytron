import os
import sys
from .interface import PlatformInterface


class LinuxImplementation(PlatformInterface):
    def __init__(self):
        import os

        self.is_native = os.environ.get("PYTRON_ENGINE") == "native"
        self.runtime_owner = "engine" if self.is_native else "platform"
        self.legacy_backend = "subprocess+ctypes"
        if not self.is_native:
            # Libraries are only needed for legacy engines
            from .linux_ops import libs

            libs.load_libs()
            if not libs.gtk:
                print("Pytron Warning: GTK3 not found. Window controls may fail.")

    def _get_native(self, w):
        """Returns the native webview instance if available."""
        return getattr(w, "native", None)

    def minimize(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.minimize()
        else:
            from .linux_ops import window

            window.minimize(w)

    def center(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.center()
        else:
            from .linux_ops import window

            window.center(w)

    def set_bounds(self, w, x, y, width, height):
        native = self._get_native(w)
        if self.is_native and native:
            native.set_bounds(int(x), int(y), int(width), int(height))
        else:
            from .linux_ops import window

            window.set_bounds(w, x, y, width, height)

    def close(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.terminate()
        else:
            from .linux_ops import window

            window.close(w)

    def toggle_maximize(self, w):
        # We don't have a direct toggle in Rust yet, so we just maximize
        native = self._get_native(w)
        if self.is_native and native:
            native.maximize()
            return True
        else:
            from .linux_ops import window

            return window.toggle_maximize(w)

    def make_frameless(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.set_decorations(False)
        else:
            from .linux_ops import window

            window.make_frameless(w)

    def start_drag(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.start_drag()
        else:
            from .linux_ops import window

            window.start_drag(w)

    def message_box(self, w, title, message, style=0):
        # Fallback to zenity/kdialog subprocess (safe from Schism)
        from .linux_ops import system

        return system.message_box(w, title, message, style)

    def hide(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.hide()
        else:
            from .linux_ops import window

            window.hide(w)

    def is_visible(self, w):
        return True  # Default for native

    def is_alive(self, w):
        native = self._get_native(w)
        return bool(native)

    def show(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.show()
        else:
            from .linux_ops import window

            window.show(w)

    def set_fullscreen(self, w, fullscreen):
        native = self._get_native(w)
        if self.is_native and native:
            native.set_fullscreen(fullscreen)
        else:
            from .linux_ops import window

            window.set_fullscreen(w, fullscreen)

    def set_always_on_top(self, w, enable):
        native = self._get_native(w)
        if self.is_native and native:
            native.set_always_on_top(enable)
        else:
            from .linux_ops import window

            window.set_always_on_top(w, enable)

    def notification(self, w, title, message, icon=None):
        from .linux_ops import system

        system.notification(w, title, message, icon)

    def open_file_dialog(self, w, title, default_path=None, file_types=None):
        from .linux_ops import system

        return system.open_file_dialog(w, title, default_path, file_types)

    def save_file_dialog(
        self, w, title, default_path=None, default_name=None, file_types=None
    ):
        from .linux_ops import system

        return system.save_file_dialog(w, title, default_path, default_name, file_types)

    def open_folder_dialog(self, w, title, default_path=None):
        from .linux_ops import system

        return system.open_folder_dialog(w, title, default_path)

    def set_taskbar_progress(self, w, state="normal", value=0, max_value=100):
        pass

    def set_window_icon(self, w, icon_path):
        pass

    def set_app_id(self, app_id):
        pass

    def set_launch_on_boot(self, app_name, exe_path, enable=True):
        from .linux_ops import system

        return system.set_launch_on_boot(app_name, exe_path, enable)

    def register_protocol(self, scheme):
        from .linux_ops import system

        return system.register_protocol(scheme)

    def get_clipboard_text(self):
        from .linux_ops import system

        return system.get_clipboard_text()

    def set_clipboard_text(self, text):
        from .linux_ops import system

        return system.set_clipboard_text(text)
