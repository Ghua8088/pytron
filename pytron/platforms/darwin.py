import os
import sys
import shlex
import subprocess
from .interface import PlatformInterface
from ..utils import resolve_native_bridge


class DarwinImplementation(PlatformInterface):
    def __init__(self):
        self.is_native = os.environ.get("PYTRON_ENGINE") == "native"
        self.runtime_owner = "engine" if self.is_native else "platform"
        self.legacy_backend = "applescript"
        self._native_bridge = None if self.is_native else resolve_native_bridge()

    def _get_native(self, w):
        return getattr(w, "native", None)

    def _call_os(self, method_name, *args):
        if self._native_bridge and hasattr(self._native_bridge, method_name):
            return getattr(self._native_bridge, method_name)(*args)
        return None

    def _run_osascript(self, script):
        try:
            proc = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True
            )
            if proc.returncode == 0:
                return proc.stdout.strip()
        except Exception:
            pass
        return None

    # --- Abstract Method Implementations (PlatformInterface) ---

    def show(self, w):
        native = self._get_native(w)
        if native:
            native.show()
        else:
            try:
                import pytron_native

                pytron_native.show(0)
            except (ImportError, AttributeError):
                self._run_osascript(
                    'tell application "System Events" to set visible of process (name of current application) to true'
                )

    def hide(self, w):
        native = self._get_native(w)
        if native:
            native.hide()
        else:
            try:
                import pytron_native

                pytron_native.hide(0)
            except (ImportError, AttributeError):
                self._run_osascript(
                    'tell application "System Events" to set visible of process (name of current application) to false'
                )

    def close(self, w):
        native = self._get_native(w)
        if native:
            native.terminate()
        else:
            try:
                import pytron_native

                pytron_native.terminate(0)
            except (ImportError, AttributeError):
                self._run_osascript("tell window 1 to close")

    def minimize(self, w):
        native = self._get_native(w)
        if native:
            native.minimize()
        else:
            try:
                import pytron_native

                pytron_native.minimize(0)
            except (ImportError, AttributeError):
                self._run_osascript("set miniaturized of window 1 to true")

    def toggle_maximize(self, w):
        native = self._get_native(w)
        if native:
            native.maximize()
            return True
        try:
            import pytron_native

            res = pytron_native.toggle_maximize(0)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass
        self.maximize(w)
        return True

    def maximize(self, w):
        native = self._get_native(w)
        if native:
            native.maximize()
        else:
            try:
                import pytron_native

                pytron_native.maximize(0)
            except (ImportError, AttributeError):
                self._run_osascript("set zoomed of window 1 to true")

    def restore(self, w):
        native = self._get_native(w)
        if native:
            if hasattr(native, "restore"):
                native.restore()
            else:
                native.unmaximize()
        else:
            try:
                import pytron_native

                pytron_native.restore(0)
            except (ImportError, AttributeError):
                self._run_osascript("set zoomed of window 1 to false")

    def set_title(self, w, title):
        native = self._get_native(w)
        if native:
            native.set_title(title)
        else:
            try:
                import pytron_native

                pytron_native.set_title(0, title)
            except (ImportError, AttributeError):
                self._run_osascript(f'set title of window 1 to "{title}"')

    def set_bounds(self, w, x, y, width, height):
        native = self._get_native(w)
        if native:
            if hasattr(native, "set_bounds"):
                native.set_bounds(int(x), int(y), int(width), int(height))
            else:
                native.set_size(int(width), int(height), 0)
        else:
            try:
                import pytron_native

                pytron_native.set_bounds(0, x, y, width, height)
            except (ImportError, AttributeError):
                # AppleScript bounds are {x1, y1, x2, y2}
                self._run_osascript(
                    f"set bounds of window 1 to {{{x}, {y}, {x+width}, {y+height}}}"
                )

    def set_fullscreen(self, w, enable):
        native = self._get_native(w)
        if native:
            native.set_fullscreen(enable)
        else:
            try:
                import pytron_native

                pytron_native.set_fullscreen(0, enable)
            except (ImportError, AttributeError):
                pass

    def set_always_on_top(self, w, enable):
        native = self._get_native(w)
        if native and hasattr(native, "set_always_on_top"):
            native.set_always_on_top(enable)
        else:
            try:
                import pytron_native

                pytron_native.set_always_on_top(0, enable)
            except (ImportError, AttributeError):
                pass

    def is_visible(self, w):
        native = self._get_native(w)
        if native:
            return True
        try:
            import pytron_native

            res = pytron_native.is_visible(0)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass
        return True

    def center(self, w):
        native = self._get_native(w)
        if native and hasattr(native, "center"):
            native.center()
        else:
            try:
                import pytron_native

                pytron_native.center(0)
            except (ImportError, AttributeError):
                pass

    def is_alive(self, w):
        return self.is_visible(w)

    # --- Extended Capabilities ---

    def make_frameless(self, w):
        native = self._get_native(w)
        if native and hasattr(native, "set_decorations"):
            native.set_decorations(False)
        else:
            pass

    def start_drag(self, w):
        native = self._get_native(w)
        if native:
            native.start_drag()
        else:
            pass

    def message_box(self, w, title, message, style=0):
        try:
            import pytron_native

            level = "informational"
            if style in (4, 5):
                level = "warning"
            res = pytron_native.message_box(0, title, message, level)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass

        script = ""
        if style == 4:
            script = f'display alert "{title}" message "{message}" buttons {{"No", "Yes"}} default button "Yes"'
        elif style == 1:
            script = f'display alert "{title}" message "{message}" buttons {{"Cancel", "OK"}} default button "OK"'
        else:
            script = f'display alert "{title}" message "{message}" buttons {{"OK"}} default button "OK"'
        output = self._run_osascript(script)
        if output and ("Yes" in output or "OK" in output):
            return 6 if style == 4 else 1
        return 7 if style == 4 else 2
        native = self._get_native(w)
        if native:
            native.start_drag()
        else:
            self._call_os("start_drag", w)

    def message_box(self, w, title, message, style=0):
        try:
            import pytron_native

            level = "informational"
            if style in (4, 5):
                level = "warning"
            res = pytron_native.message_box(0, title, message, level)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass

        script = ""
        if style == 4:
            script = f'display alert "{title}" message "{message}" buttons {{"No", "Yes"}} default button "Yes"'
        elif style == 1:
            script = f'display alert "{title}" message "{message}" buttons {{"Cancel", "OK"}} default button "OK"'
        else:
            script = f'display alert "{title}" message "{message}" buttons {{"OK"}} default button "OK"'
        output = self._run_osascript(script)
        if output and ("Yes" in output or "OK" in output):
            return 6 if style == 4 else 1
        return 7 if style == 4 else 2

    def notification(self, w, title, message, icon=None):
        try:
            import pytron_native

            pytron_native.show_notification(0, title, message, icon)
            return
        except (ImportError, AttributeError):
            pass

        script = f'display notification "{message}" with title "{title}"'
        try:
            subprocess.Popen(["osascript", "-e", script])
        except Exception:
            pass

    def open_file_dialog(self, w, title, default_path=None, file_types=None):
        try:
            import pytron_native

            res = pytron_native.open_file_dialog(0, title, default_path, file_types)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass

        script = f'POSIX path of (choose file with prompt "{title}"'
        if default_path:
            script += f' default location "{default_path}"'
        script += ")"
        return self._run_osascript(script)

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

        script = f'POSIX path of (choose file name with prompt "{title}"'
        if default_path:
            script += f' default location "{default_path}"'
        if default_name:
            script += f' default name "{default_name}"'
        script += ")"
        return self._run_osascript(script)

    def open_folder_dialog(self, w, title, default_path=None):
        try:
            import pytron_native

            res = pytron_native.open_folder_dialog(0, title, default_path)
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass

        script = f'POSIX path of (choose folder with prompt "{title}"'
        if default_path:
            script += f' default location "{default_path}"'
        script += ")"
        return self._run_osascript(script)

    def register_protocol(self, scheme):
        # On Mac it mostly calls lsregister if bundled
        # Current impl in DarwinImplementation was missing, adding a basic version
        # using lsregister if bundled.
        if getattr(sys, "frozen", False):
            try:
                exe = sys.executable
                subprocess.run(
                    [
                        "/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister",
                        "-f",
                        exe,
                    ],
                    capture_output=True,
                )
                return True
            except Exception:
                pass
        return False

    def set_app_id(self, app_id):
        pass

    def set_window_icon(self, w, icon_path):
        pass

    def set_taskbar_progress(self, w, state="normal", value=0, max_value=100):
        pass

    def get_clipboard_text(self):
        try:
            import pytron_native

            res = pytron_native.get_clipboard_text()
            if res is not None:
                return res
        except (ImportError, AttributeError):
            pass

        try:
            return subprocess.check_output(["pbpaste"], text=True).strip()
        except Exception:
            return None

    def set_clipboard_text(self, text):
        try:
            import pytron_native

            res = pytron_native.set_clipboard_text(text)
            if res is not None:
                return bool(res)
        except (ImportError, AttributeError):
            pass

        try:
            subprocess.run(
                ["pbcopy"],
                input=text,
                text=True,
                check=True,
                capture_output=True,
            )
            return True
        except Exception:
            return False
