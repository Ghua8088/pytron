import os
import shlex
import subprocess
from .interface import PlatformInterface
from ..utils import resolve_os_module


class DarwinImplementation(PlatformInterface):
    def __init__(self):
        self.is_native = os.environ.get("PYTRON_ENGINE") == "native"
        self.runtime_owner = "engine" if self.is_native else "platform"
        self.legacy_backend = "applescript"
        self._pytron_os = None if self.is_native else resolve_os_module()

    def _get_native(self, w):
        return getattr(w, "native", None)

    def _call_os(self, method_name, *args):
        if self._pytron_os and hasattr(self._pytron_os, method_name):
            return getattr(self._pytron_os, method_name)(*args)
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

    def minimize(self, w):
        native = self._get_native(w)
        if native:
            native.minimize()
        else:
            self._call_os("minimize", w)

    def center(self, w):
        native = self._get_native(w)
        if native and hasattr(native, "center"):
            native.center()
        else:
            self._call_os("center", w)

    def set_bounds(self, w, x, y, width, height):
        native = self._get_native(w)
        if native and hasattr(native, "set_bounds"):
            native.set_bounds(int(x), int(y), int(width), int(height))
        else:
            self._call_os("set_bounds", w, x, y, width, height)

    def close(self, w):
        native = self._get_native(w)
        if native:
            native.terminate()
        else:
            self._call_os("close", w)

    def toggle_maximize(self, w):
        native = self._get_native(w)
        if native:
            native.maximize()
            return True
        res = self._call_os("toggle_maximize", w)
        return bool(res) if res is not None else True

    def make_frameless(self, w):
        native = self._get_native(w)
        if native and hasattr(native, "set_decorations"):
            native.set_decorations(False)
        else:
            self._call_os("make_frameless", w)

    def start_drag(self, w):
        native = self._get_native(w)
        if native:
            native.start_drag()
        else:
            self._call_os("start_drag", w)

    def message_box(self, w, title, message, style=0):
        level = "informational"
        if style in (4, 5):
            level = "warning"
        result = self._call_os("message_box", w, title, message, level)
        if result is not None:
            return result

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

    def hide(self, w):
        native = self._get_native(w)
        if native:
            native.hide()
        else:
            self._call_os("hide", w)

    def is_visible(self, w):
        native = self._get_native(w)
        if native:
            return True
        res = self._call_os("is_visible", w)
        return bool(res) if res is not None else True

    def is_alive(self, w):
        native = self._get_native(w)
        return bool(native)

    def show(self, w):
        native = self._get_native(w)
        if native:
            native.show()
        else:
            self._call_os("show", w)

    def set_fullscreen(self, w, fullscreen):
        native = self._get_native(w)
        if native:
            native.set_fullscreen(fullscreen)
        else:
            self._call_os("set_fullscreen", w, fullscreen)

    def set_always_on_top(self, w, enable):
        native = self._get_native(w)
        if native and hasattr(native, "set_always_on_top"):
            native.set_always_on_top(enable)
        else:
            self._call_os("set_always_on_top", w, enable)

    def notification(self, w, title, message, icon=None):
        if self._call_os("show_notification", w, title, message, icon) is not None:
            return
        script = f'display notification "{message}" with title "{title}"'
        try:
            subprocess.Popen(["osascript", "-e", script])
        except Exception:
            pass

    def open_file_dialog(self, w, title, default_path=None, file_types=None):
        res = self._call_os("open_file_dialog", w, title, default_path, file_types)
        if res is not None:
            return res
        script = f'POSIX path of (choose file with prompt "{title}"'
        if default_path:
            script += f' default location "{default_path}"'
        script += ")"
        return self._run_osascript(script)

    def save_file_dialog(
        self, w, title, default_path=None, default_name=None, file_types=None
    ):
        res = self._call_os(
            "save_file_dialog", w, title, default_path, default_name, file_types
        )
        if res is not None:
            return res
        script = f'POSIX path of (choose file name with prompt "{title}"'
        if default_path:
            script += f' default location "{default_path}"'
        if default_name:
            script += f' default name "{default_name}"'
        script += ")"
        return self._run_osascript(script)

    def open_folder_dialog(self, w, title, default_path=None):
        res = self._call_os("open_folder_dialog", w, title, default_path)
        if res is not None:
            return res
        script = f'POSIX path of (choose folder with prompt "{title}"'
        if default_path:
            script += f' default location "{default_path}"'
        script += ")"
        return self._run_osascript(script)

    def set_taskbar_progress(self, w, state="normal", value=0, max_value=100):
        self._call_os("set_taskbar_progress", w, state, value, max_value)

    def set_window_icon(self, w, icon_path):
        self._call_os("set_window_icon", w, icon_path)

    def set_app_id(self, app_id):
        # Runtime bundle id is immutable on macOS; only subprocess engines should
        # attempt pytron_os hooks here.
        self._call_os("set_app_id", app_id)

    def set_launch_on_boot(self, app_name, exe_path, enable=True):
        res = self._call_os("set_launch_on_boot", app_name, exe_path, enable)
        if res is not None:
            return res

        home = os.path.expanduser("~")
        launch_agents = os.path.join(home, "Library/LaunchAgents")
        plist_file = os.path.join(
            launch_agents, f"com.{app_name.lower()}.startup.plist"
        )

        if enable:
            try:
                os.makedirs(launch_agents, exist_ok=True)
                args = shlex.split(exe_path)
                array_str = "\n".join([f"    <string>{a}</string>" for a in args])
                content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{app_name.lower()}.startup</string>
    <key>ProgramArguments</key>
    <array>
{array_str}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
                with open(plist_file, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
            except Exception:
                return False

        try:
            if os.path.exists(plist_file):
                os.remove(plist_file)
            return True
        except Exception:
            return False

    def register_protocol(self, scheme):
        # Protocol registration still fundamentally belongs in the bundled app's
        # Info.plist, but we preserve the Launch Services refresh hook for bundled
        # apps so existing packaged-app flows keep working.
        try:
            import sys

            if getattr(sys, "frozen", False):
                exec_path = sys.executable
                if ".app/Contents/MacOS/" in exec_path:
                    app_path = exec_path.split(".app/Contents/MacOS/")[0] + ".app"
                    lsregister_path = "/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister"
                    if os.path.exists(lsregister_path):
                        subprocess.run(
                            [lsregister_path, "-f", app_path], capture_output=True
                        )
                        return True
            return False
        except Exception:
            return False

    def set_clipboard_text(self, text):
        res = self._call_os("set_clipboard_text", text)
        if res is not None:
            return bool(res)
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

    def get_clipboard_text(self):
        res = self._call_os("get_clipboard_text")
        if res is not None:
            return res
        try:
            return subprocess.check_output(["pbpaste"], text=True).strip()
        except Exception:
            return None
