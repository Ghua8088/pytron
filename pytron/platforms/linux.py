import os
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

    # --- Abstract Method Implementations (PlatformInterface) ---

    def show(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.show()
        else:
            try:
                import pytron_native

                pytron_native.show(w.hwnd if hasattr(w, "hwnd") else 0)
            except (ImportError, AttributeError):
                from .linux_ops import window

                window.show(w)

    def hide(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.hide()
        else:
            try:
                import pytron_native

                pytron_native.hide(w.hwnd if hasattr(w, "hwnd") else 0)
            except (ImportError, AttributeError):
                from .linux_ops import window

                window.hide(w)

    def close(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.terminate()
        else:
            try:
                import pytron_native

                pytron_native.terminate(w.hwnd if hasattr(w, "hwnd") else 0)
            except (ImportError, AttributeError):
                from .linux_ops import window

                window.close(w)

    def minimize(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.minimize()
        else:
            try:
                import pytron_native

                pytron_native.minimize(w.hwnd if hasattr(w, "hwnd") else 0)
            except (ImportError, AttributeError):
                from .linux_ops import window

                window.minimize(w)

    def toggle_maximize(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.maximize()
            return True
        try:
            import pytron_native

            res = pytron_native.toggle_maximize(w.hwnd if hasattr(w, "hwnd") else 0)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            from .linux_ops import window

            return window.toggle_maximize(w)
        return False

    def maximize(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.maximize()
        else:
            try:
                import pytron_native

                pytron_native.maximize(w.hwnd if hasattr(w, "hwnd") else 0)
            except (ImportError, AttributeError):
                from .linux_ops import window

                window.maximize(w)

    def restore(self, w):
        native = self._get_native(w)
        if self.is_native and native:
            native.unmaximize()
        else:
            try:
                import pytron_native

                pytron_native.restore(w.hwnd if hasattr(w, "hwnd") else 0)
            except (ImportError, AttributeError):
                from .linux_ops import window

                window.restore(w)

    def set_title(self, w, title):
        native = self._get_native(w)
        if self.is_native and native:
            native.set_title(title)
        else:
            try:
                import pytron_native

                pytron_native.set_title(w.hwnd if hasattr(w, "hwnd") else 0, title)
            except (ImportError, AttributeError):
                from .linux_ops import window

                window.set_title(w, title)

    def set_bounds(self, w, x, y, width, height):
        native = self._get_native(w)
        if self.is_native and native:
            if hasattr(native, "set_bounds"):
                native.set_bounds(int(x), int(y), int(width), int(height))
            else:
                native.set_size(int(width), int(height), 0)
        else:
            try:
                import pytron_native

                pytron_native.set_bounds(
                    w.hwnd if hasattr(w, "hwnd") else 0, x, y, width, height
                )
            except (ImportError, AttributeError):
                from .linux_ops import window

                window.set_bounds(w, x, y, width, height)

    def set_fullscreen(self, w, fullscreen):
        native = self._get_native(w)
        if self.is_native and native:
            native.set_fullscreen(fullscreen)
        else:
            try:
                import pytron_native

                pytron_native.set_fullscreen(
                    w.hwnd if hasattr(w, "hwnd") else 0, fullscreen
                )
            except (ImportError, AttributeError):
                from .linux_ops import window

                window.set_fullscreen(w, fullscreen)

    def set_always_on_top(self, w, enable):
        native = self._get_native(w)
        if self.is_native and native:
            native.set_always_on_top(enable)
        else:
            try:
                import pytron_native

                pytron_native.set_always_on_top(
                    w.hwnd if hasattr(w, "hwnd") else 0, enable
                )
            except (ImportError, AttributeError):
                from .linux_ops import window

                window.set_always_on_top(w, enable)

    def is_visible(self, w):
        native = self._get_native(w)
        if native:
            return True
        try:
            import pytron_native

            res = pytron_native.is_visible(w.hwnd if hasattr(w, "hwnd") else 0)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass
        return True

    def center(self, w):
        native = self._get_native(w)
        if self.is_native and native and hasattr(native, "center"):
            native.center()
        else:
            try:
                import pytron_native

                pytron_native.center(w.hwnd if hasattr(w, "hwnd") else 0)
            except (ImportError, AttributeError):
                from .linux_ops import window

                window.center(w)

    def is_alive(self, w):
        return self.is_visible(w)

    # --- Extended Capabilities (Virtual) ---

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
        try:
            import pytron_native

            res = pytron_native.message_box(0, title, message, style)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass
        from .linux_ops import system

        return system.message_box(w, title, message, style)

    def notification(self, w, title, message, icon=None):
        try:
            import pytron_native

            pytron_native.show_notification(0, title, message, icon)
            return
        except (ImportError, AttributeError):
            pass
        from .linux_ops import system

        system.notification(w, title, message, icon)

    def open_file_dialog(self, w, title, default_path=None, file_types=None):
        try:
            import pytron_native

            res = pytron_native.open_file_dialog(0, title, default_path, file_types)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass
        from .linux_ops import system

        return system.open_file_dialog(w, title, default_path, file_types)

    def save_file_dialog(
        self, w, title, default_path=None, default_name=None, file_types=None
    ):
        try:
            import pytron_native

            res = pytron_native.save_file_dialog(
                0, title, default_path, default_name, file_types
            )
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass
        from .linux_ops import system

        return system.save_file_dialog(w, title, default_path, default_name, file_types)

    def open_folder_dialog(self, w, title, default_path=None):
        try:
            import pytron_native

            res = pytron_native.open_folder_dialog(0, title, default_path)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass
        from .linux_ops import system

        return system.open_folder_dialog(w, title, default_path)

    def set_taskbar_progress(self, w, state="normal", value=0, max_value=100):
        try:
            import pytron_native

            pytron_native.set_taskbar_progress(
                w.hwnd if hasattr(w, "hwnd") else 0, state, value, max_value
            )
        except (ImportError, AttributeError):
            pass

    def set_window_icon(self, w, icon_path):
        try:
            import pytron_native

            pytron_native.set_window_icon(
                w.hwnd if hasattr(w, "hwnd") else 0, icon_path
            )
        except (ImportError, AttributeError):
            pass

    def set_app_id(self, app_id):
        try:
            import pytron_native

            pytron_native.set_app_id(app_id)
        except (ImportError, AttributeError):
            pass

    def set_launch_on_boot(self, app_name, exe_path, enable=True):
        try:
            import pytron_native

            res = pytron_native.set_launch_on_boot(app_name, exe_path, enable)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass
        from .linux_ops import system

        return system.set_launch_on_boot(app_name, exe_path, enable)

    def register_protocol(self, scheme):
        from .linux_ops import system

        return system.register_protocol(scheme)

    def get_clipboard_text(self):
        try:
            import pytron_native

            res = pytron_native.get_clipboard_text()
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass
        from .linux_ops import system

        return system.get_clipboard_text()

    def set_clipboard_text(self, text):
        try:
            import pytron_native

            res = pytron_native.set_clipboard_text(text)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass
        from .linux_ops import system

        return system.set_clipboard_text(text)

    def get_system_info(self):
        import platform

        return {
            "os": "linux",
            "arch": platform.machine(),
            "cpu_count": os.cpu_count(),
            "release": platform.release(),
            "version": platform.version(),
        }
