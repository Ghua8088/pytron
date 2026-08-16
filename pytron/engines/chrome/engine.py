import os
import sys
import json
import logging
import ctypes
import subprocess
from typing import Optional
from ...webview import Webview
from .adapter import ChromeAdapter


def _to_str(b):
    if isinstance(b, bytes):
        return b.decode("utf-8")
    if hasattr(b, "value") and isinstance(b.value, bytes):  # ctypes.c_char_p
        return b.value.decode("utf-8")
    return str(b)


class ChromeBridge:
    """Mocks the native 'lib' DLL interface but redirects to Chrome Shell via IPC."""

    def __init__(self, adapter):
        self.adapter = adapter
        self._callbacks = {}
        self.real_hwnd = 0

    def create(self, debug, window, root_path=None):
        self.adapter.send(
            {
                "action": "init",
                "options": {
                    "debug": bool(debug),
                    "root": root_path,
                    "app_id": self.adapter.config.get("app_id", ""),
                    "frameless": self.adapter.config.get("frameless", False),
                    "icon": self.adapter.config.get("icon", ""),
                    "width": self.adapter.config.get("width", 1024),
                    "height": self.adapter.config.get("height", 768),
                    "title": self.adapter.config.get("title", "Pytron"),
                    "min_size": self.adapter.config.get("min_size"),
                    "max_size": self.adapter.config.get("max_size"),
                    "resizable": self.adapter.config.get("resizable", True),
                    "fullscreen": self.adapter.config.get("fullscreen", False),
                    "always_on_top": self.adapter.config.get("always_on_top", False),
                    "background_color": self.adapter.config.get(
                        "background_color", "#ffffff"
                    ),
                    "start_hidden": self.adapter.config.get("start_hidden", False),
                    "start_maximized": self.adapter.config.get(
                        "start_maximized", False
                    ),
                    "start_minimized": self.adapter.config.get(
                        "start_minimized", False
                    ),
                    "transparent": self.adapter.config.get("transparent", False),
                    "center": self.adapter.config.get("center", True),
                    "theme": self.adapter.config.get("theme", "light"),
                },
            }
        )
        return 1

    def drag(self, w=None):
        """Initiates window dragging from the renderer."""
        self.adapter.send({"action": "start_drag"})

    def show(self, w=None):
        self.adapter.send({"action": "show"})

    def hide(self, w=None):
        self.adapter.send({"action": "hide"})

    def set_title(self, title, w=None):
        self.adapter.send({"action": "set_title", "title": _to_str(title)})

    def set_icon(self, icon_path, w=None):
        self.adapter.send({"action": "set_icon", "icon": str(icon_path)})

    def set_size(self, width, height, hints=None, w=None):
        self.adapter.send({"action": "set_size", "width": width, "height": height})

    def navigate(self, url, w=None):
        self.adapter.send({"action": "navigate", "url": _to_str(url)})

    def eval(self, js, w=None):
        self.adapter.send({"action": "eval", "code": _to_str(js)})

    def init_script(self, js, w=None):
        self.adapter.send({"action": "init_script", "js": _to_str(js)})

    def run(self, w=None):
        if self.adapter.process:
            self.adapter.process.wait()

    def terminate(self, w=None):
        self.adapter.send({"action": "close"})

    def bind(self, name, fn, arg=None, w=None):
        n = _to_str(name)
        self._callbacks[n] = fn
        self.adapter.send({"action": "bind", "name": n})

    def return_result(self, seq, status, result, w=None):
        try:
            if result is None:
                res_obj = None
            else:
                res_obj = json.loads(_to_str(result))
        except Exception:
            res_obj = _to_str(result)

        self.adapter.send(
            {"action": "reply", "id": _to_str(seq), "status": status, "result": res_obj}
        )

    def get_hwnd(self, w=None):
        # On Windows, returning the real HWND allows native features (Taskbar, Menus) to work.
        if sys.platform == "win32":
            return self.real_hwnd
        return 0

    def create_tray(self, icon_path, tooltip="Pytron App"):
        self.adapter.send(
            {"action": "create_tray", "icon": str(icon_path), "tooltip": tooltip}
        )

    def dispatch(self, w, fn, arg):
        try:
            js_code = _to_str(ctypes.cast(arg, ctypes.c_char_p))
            self.eval(js_code)
        except Exception:
            pass




class ChromeWebView(Webview):
    """
    Electronic Mojo Engine for Pytron.
    A professional, Chromium-based alternative to the native webview.
    """

    def __init__(self, config):
        # 1. Initialize Base (Components, Loops, Infra)
        super().__init__(config)
        self.logger = logging.getLogger("Pytron.ChromeWebView")

        # 2. Resolve Chrome Binary
        shell_path = config.get("engine_path")
        if not shell_path:
            shell_path = self._resolve_chrome_binary(config)

        if not shell_path or not os.path.exists(shell_path):
            from .forge import ChromeForge

            self.logger.warning("Chrome Engine not found. Auto-provisioning...")
            forge = ChromeForge()
            shell_path = forge.provision()

        # 3. Path & URL Setup
        navigate_url = self._routing_comp.normalize_to_pytron(config.get("url", ""))
        self._start_url = navigate_url
        root_path = self._routing_comp.root_path

        if "cwd" not in config:
            config["cwd"] = root_path

        # 4. Initialize Bridge & Start Adapter
        self.logger.info(f"Using Chrome Shell (v3): {shell_path}")
        self.adapter = ChromeAdapter(shell_path, config)
        self.bridge = ChromeBridge(self.adapter)
        self.native = self.bridge  # For facade compatibility

        # Initialize Platform Implementation (Required for DialogComponent to use system hooks)
        if sys.platform == "win32":
            from ...platforms import WindowsImplementation

            self._platform = WindowsImplementation()
        elif sys.platform == "darwin":
            from ...platforms import MacOSImplementation

            self._platform = MacOSImplementation()
        elif sys.platform.startswith("linux"):
            from ...platforms import LinuxImplementation

            self._platform = LinuxImplementation()

        self.adapter.start()
        self.adapter.bind_raw(self._handle_ipc_message)
        self._pending_geometry = []

        # 5. Setup Icon & Create Window
        self._setup_icon(config)
        self.w = self.bridge.create(
            config.get("debug", False), self, root_path=root_path
        )

        self._ipc_comp.init_core_bindings()

        self.set_title(config.get("title", "Pytron App"))

        w, h = config.get("dimensions", [800, 600])
        self.set_size(w, h)
        if config.get("center", True):
            self.center(w, h)

        if not config.get("start_hidden", False):
            self.show()

        # 6. Navigate
        self.navigate(navigate_url)

        # 7. JS Init Shim (With Proxy for Dynamic Methods)
        # Injected via init_script so it runs on every page load, not just once.
        # NOTE: Previously this was dead code trapped inside _resolve_chrome_binary
        # after a return statement — it never ran. Fixed here.
        init_js = f"""
        (function() {{
            try {{
                if (!window.pytron) {{
                    window.pytron = {{ is_ready: true, id: "{self.id}" }};
                }} else {{
                    window.pytron.is_ready = true;
                    window.pytron.id = "{self.id}";
                }}
            }} catch (e) {{
                // Already read-only or handled by bridge
            }}

            window.pytron_is_native = true;

            // --- DE-BROWSERIFY CORE ---
            (function() {{
                const isDebug = {str(self.config.get("debug", False)).lower()};

                // 1. Kill Context Menu (Unless debugging)
                if (!isDebug) {{
                    document.addEventListener('contextmenu', e => e.preventDefault());
                }}

                // 2. Kill "Ghost" Drags (images/links flying around)
                document.addEventListener('dragstart', e => {{
                    if (e.target.tagName === 'IMG' || e.target.tagName === 'A') e.preventDefault();
                }});

                // 3. Kill Browser Shortcuts
                window.addEventListener('keydown', e => {{
                    const forbidden = ['r', 'p', 's', 'j', 'u', 'f'];
                    if (e.ctrlKey && forbidden.includes(e.key.toLowerCase())) e.preventDefault();
                    if (e.key === 'F5' || e.key === 'F3' || (e.ctrlKey && e.key === 'f')) e.preventDefault();
                    // Block Zoom
                    if (e.ctrlKey && (e.key === '=' || e.key === '-' || e.key === '0')) e.preventDefault();
                }}, true);

                // 4. Kill System UI Styles (Selection, Outlines, Rubber-banding)
                const style = document.createElement('style');
                style.textContent = `
                    * {{
                        -webkit-user-select: none;
                        user-select: none;
                        -webkit-user-drag: none;
                        -webkit-tap-highlight-color: transparent;
                        outline: none !important;
                    }}
                    input, textarea, [contenteditable], [contenteditable] * {{
                        -webkit-user-select: text !important;
                        user-select: text !important;
                    }}
                    html, body {{
                        overscroll-behavior: none !important;
                        cursor: default;
                    }}
                    a, button, input[type="button"], input[type="submit"] {{
                        cursor: pointer;
                    }}
                `;
                document.head ? document.head.appendChild(style) : document.addEventListener('DOMContentLoaded', () => document.head.appendChild(style));
            }})();

            // Universal IPC Bridge
            if (!window.__pytron_native_bridge) {{
                window.__pytron_native_bridge = (method, args) => {{
                    const seq = Math.random().toString(36).substring(2, 10);
                    if (window.ipc) {{
                         window.ipc.postMessage(JSON.stringify({{id: seq, method: method, params: args}}));
                    }}
                    return new Promise((resolve, reject) => {{
                        window._rpc = window._rpc || {{}};
                        window._rpc[seq] = {{resolve, reject}};
                    }});
                }};
            }}

            // Dynamic Proxy to handle ANY method call from frontend (hide, center, etc.)
            try {{
                const existing = window.pytron;
                window.pytron = new Proxy(existing || {{}}, {{
                    get: function(target, prop) {{
                        if (prop in target) return target[prop];
                        // If not found, assume it's a bridge call
                        return (...args) => window.__pytron_native_bridge(prop, args);
                    }}
                }});
            }} catch (e) {{
                // Skip proxy if window.pytron is read-only
            }}

            // Standard Pollys & Asset Bridge
            window.pytron_drag = () => {{ if (window.__pytron_native_bridge && window.__pytron_native_bridge.emit) window.__pytron_native_bridge.emit('pytron_drag', {{ data: [] }}); }};
            window.pytron_minimize = () => {{ if (window.__pytron_native_bridge && window.__pytron_native_bridge.emit) window.__pytron_native_bridge.emit('pytron_minimize', {{ data: [] }}); }};
            window.pytron_get_asset = (key) => {{ if (window.__pytron_native_bridge && window.__pytron_native_bridge.emit) window.__pytron_native_bridge.emit('pytron_get_asset', {{ data: [key] }}); }};

            window['pytron_drag'] = window.pytron_drag;
            window['pytron_minimize'] = window.pytron_minimize;
            window['pytron_get_asset'] = window.pytron_get_asset;
            window['__pytron_vap_get'] = window.pytron_get_asset;

        }})();
        """
        self.bridge.init_script(init_js)

        # Force Resizable Update (Fix gray maximize button)
        # Sometimes init flag is overridden by window style defaults in Electron
        self.adapter.send({"action": "set_resizable", "resizable": True})

    def _setup_icon(self, config):
        """Resolves and sets the window icon."""
        icon_raw = (
            config.get("icon")
            or config.get("app_icon")
            or self.adapter.config.get("icon")
        )
        if icon_raw:
            resolved = None
            if os.path.exists(icon_raw):
                resolved = os.path.abspath(icon_raw)
            else:
                from ...utils import get_resource_path

                res = get_resource_path(icon_raw)
                if res and os.path.exists(res):
                    resolved = os.path.abspath(res)

                root = (
                    getattr(self._routing_comp, "root_path", None)
                    if hasattr(self, "_routing_comp")
                    else None
                )
                if not resolved and root:
                    possible = os.path.join(root, icon_raw)
                    if os.path.exists(possible):
                        resolved = os.path.abspath(possible)
                if (
                    not resolved
                    and getattr(sys, "frozen", False)
                    and hasattr(sys, "_MEIPASS")
                ):
                    meipass_cand = os.path.join(sys._MEIPASS, icon_raw)
                    if os.path.exists(meipass_cand):
                        resolved = os.path.abspath(meipass_cand)

            if not resolved:
                from ...utils import get_resource_path

                for cand in [
                    get_resource_path(os.path.join("resources", "app_icon.ico")),
                    get_resource_path(os.path.join("resources", "app_icon.png")),
                    get_resource_path("app_icon.ico"),
                    get_resource_path("app_icon.png"),
                ]:
                    if cand and os.path.exists(cand):
                        resolved = os.path.abspath(cand)
                        break

            target_icon = resolved or icon_raw
            config["icon"] = target_icon
            self.adapter.config["icon"] = target_icon

        if config.get("icon"):
            self.set_icon(config["icon"])

    def _resolve_chrome_binary(self, config) -> Optional[str]:
        """Chrome-specific binary detection logic."""
        if getattr(sys, "frozen", False):
            exe_name = os.path.splitext(os.path.basename(sys.executable))[0]
            candidates = [
                f"{exe_name}.exe",
                f"{exe_name}-Renderer.exe",
                f"{exe_name}-Engine.exe",
                "electron.exe",
            ]
            base_dir = os.path.dirname(sys.executable)
            search_roots = [
                base_dir,
                os.path.join(base_dir, "pytron", "dependencies", "chrome"),
                (
                    os.path.join(
                        getattr(sys, "_MEIPASS", ""), "pytron", "dependencies", "chrome"
                    )
                    if hasattr(sys, "_MEIPASS")
                    else None
                ),
            ]
            for root in filter(None, search_roots):
                if not os.path.exists(root):
                    continue
                for candidate in candidates:
                    path = os.path.join(root, candidate)
                    if os.path.exists(path) and os.path.abspath(
                        path
                    ) != os.path.abspath(sys.executable):
                        return path

        global_path = os.path.expanduser("~/.pytron/engines/chrome/electron.exe")
        if os.path.exists(global_path):
            return global_path

        dev_path = os.path.abspath(
            os.path.join(
                os.getcwd(), "..", "pytron-electron-engine", "bin", "electron.exe"
            )
        )
        if os.path.exists(dev_path):
            return dev_path
        return None

    @property
    def hwnd(self):
        """Override to return Electron HWND instead of native engine HWND."""
        if hasattr(self.bridge, "real_hwnd"):
            res = self.bridge.real_hwnd
            if isinstance(res, (int, float)):
                return int(res)
        return 0

    def _handle_ipc_message(self, msg):

        msg_type = msg.get("type")
        payload = msg.get("payload")

        # DEBUG: Log all lifecycle events to trace HWND
        if msg_type == "lifecycle":
            self.logger.info(f"Chrome Lifecycle Event: {payload}")

        # HWND Sync
        if (
            msg_type == "lifecycle"
            and isinstance(payload, dict)
            and payload.get("event") == "window_created"
        ):
            hwnd_str = payload.get("hwnd")
            try:
                self.bridge.real_hwnd = int(hwnd_str)
                self.logger.info(f"Acquired Electron HWND: {self.bridge.real_hwnd}")
                # Initial curvature enforcement
                self._platform.set_window_curvature(self.bridge.real_hwnd)
                # Enforce native window icon on HWND
                icon_path = self.config.get("icon") or self.adapter.config.get("icon")
                if icon_path and hasattr(self._platform, "set_window_icon"):
                    self._platform.set_window_icon(self.bridge.real_hwnd, icon_path)
            except Exception as e:
                self.logger.error(f"Failed to process window_created: {e}")

            return

        if msg_type == "lifecycle" and payload == "ready":
            # Flush pending geometry calls off-thread perfectly in sync with DWM render
            if hasattr(self, "_pending_geometry") and self._pending_geometry:
                import threading
                import time

                queue = list(self._pending_geometry)
                self._pending_geometry.clear()

                def flush_queue(cmds):
                    # We don't need a huge delay now because 'ready' implies the Chromium
                    # backend is already fully surfaced and painted in DWM!
                    time.sleep(0.01)
                    for action, args in cmds:
                        try:
                            if action == "center":
                                self.center(*args)
                            elif action == "set_size":
                                self.set_size(*args)
                            elif action == "set_bounds":
                                self.set_bounds(*args)
                        except Exception as flush_err:
                            self.logger.debug(f"Error flushing {action}: {flush_err}")

                threading.Thread(target=flush_queue, args=(queue,), daemon=True).start()
            return

        # Curvature Persistence on State Change
        if (
            msg_type == "lifecycle"
            and isinstance(payload, dict)
            and payload.get("event") in ["unmaximize", "restore"]
        ):
            if hasattr(self.bridge, "real_hwnd") and self.bridge.real_hwnd:
                self.logger.debug(
                    f"Re-applying Curvature for event: {payload.get('event')}"
                )
                # asyncio.create_task() requires a running event loop, which is NOT
                # guaranteed here — this is called from a plain IPC reader thread.
                # Use a daemon thread with a short sleep instead (same effect, always safe).
                import threading
                import time

                hwnd = self.bridge.real_hwnd

                def _delayed_curvature():
                    time.sleep(0.1)
                    try:
                        self._platform.set_window_curvature(hwnd)
                    except Exception as e:
                        self.logger.debug(f"Delayed curvature error: {e}")

                threading.Thread(target=_delayed_curvature, daemon=True).start()
            return

        if msg_type == "ipc":
            event = payload.get("event")
            inner_payload = payload.get("data", {})
            if isinstance(inner_payload, dict) and "data" in inner_payload:
                args = inner_payload.get("data", [])
                seq = inner_payload.get("id")
            else:
                args = inner_payload
                seq = None

            if hasattr(self.bridge, "_callbacks") and event in self.bridge._callbacks:
                func = self.bridge._callbacks[event]
                try:
                    # Delegate directly to the IPCComponent wrapper
                    # This handles thread pooling, async, serialization, and results
                    func(seq, args)
                except Exception as e:
                    self.logger.error(f"Mojo IPC Callback Error in {event}: {e}")

    async def _reapply_curvature_delayed(self):
        """Small delay to ensure Windows has finished state transition."""
        import asyncio

        await asyncio.sleep(0.1)
        if hasattr(self.bridge, "real_hwnd") and self.bridge.real_hwnd:
            self._platform.set_window_curvature(self.bridge.real_hwnd)

    # --- Feature Overrides (Compatibility Layer) ---

    def center(self, width=None, height=None):
        if not hasattr(self, "hwnd") or not self.hwnd:
            self._pending_geometry.append(("center", (width, height)))
            return

        if sys.platform == "win32":
            import ctypes
            import ctypes.wintypes

            user32 = ctypes.windll.user32

            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(rect))

            current_width = rect.right - rect.left
            current_height = rect.bottom - rect.top

            if width is None:
                width = current_width
            if height is None:
                height = current_height

            if width <= 0 or height <= 0:
                width, height = 800, 600

            hmon = user32.MonitorFromWindow(self.hwnd, 2)

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_uint),
                    ("rcMonitor", ctypes.wintypes.RECT),
                    ("rcWork", ctypes.wintypes.RECT),
                    ("dwFlags", ctypes.c_uint),
                ]

            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)

            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                r = mi.rcWork
                screen_width = r.right - r.left
                screen_height = r.bottom - r.top
                x = r.left + (screen_width - width) // 2
                y = r.top + (screen_height - height) // 2
            else:
                screen_width = user32.GetSystemMetrics(0)
                screen_height = user32.GetSystemMetrics(1)
                x = (screen_width - width) // 2
                y = (screen_height - height) // 2

            self.set_bounds(int(x), int(y), int(width), int(height))
        else:
            self.bridge.adapter.send({"action": "center"})

    def serve_data(self, key, data, mime="application/octet-stream"):
        """Sends binary data to the Node process for pytron:// serving."""
        import base64

        try:
            b64_data = base64.b64encode(data).decode("utf-8")
            self.bridge.adapter.send(
                {
                    "action": "serve_data",
                    "key": key,
                    "data": b64_data,
                    "mime": mime,
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to serve data for key {key}: {e}")

    def unserve_data(self, key):
        self.bridge.adapter.send({"action": "unserve_data", "key": key})

    def set_icon(self, icon_path):
        self.bridge.set_icon(icon_path)

    def minimize(self):
        self.adapter.send({"action": "minimize"})

    def maximize(self):
        self.adapter.send({"action": "maximize"})

    def restore(self):
        self.adapter.send({"action": "restore"})

    def drag(self):
        """Initiates window dragging."""
        self.bridge.drag()

    def show(self):
        self.bridge.show()

    def hide(self):
        self.bridge.hide()

    def close(self, force=False):
        self.bridge.terminate()

    def set_title(self, title):
        self.bridge.set_title(title)

    def set_size(self, w, h):
        if not hasattr(self, "hwnd") or not self.hwnd:
            self._pending_geometry.append(("set_size", (w, h)))
            return

        if sys.platform == "win32":
            import ctypes
            import ctypes.wintypes

            user32 = ctypes.windll.user32

            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(rect))

            # Use current origin, but new size!
            self.set_bounds(rect.left, rect.top, int(w), int(h))
        else:
            self.bridge.set_size(w, h)

    def navigate(self, url):
        self.bridge.navigate(url)

    def eval(self, js):
        self.bridge.eval(js)

    def toggle_maximize(self):
        self.bridge.adapter.send({"action": "toggle_maximize"})

    def make_frameless(self):
        self.bridge.adapter.send({"action": "set_frameless", "frameless": True})

    def start_drag(self):
        try:
            self.adapter.send({"action": "start_drag"})
        except Exception as e:
            self.logger.debug(f"start_drag not supported by shell: {e}")

    def set_menu(self, menu_bar):
        # Forward a simple menu structure to the shell process. The shell may ignore unknown fields.
        try:
            self.adapter.send({"action": "set_menu", "menu": menu_bar})
        except Exception as e:
            self.logger.debug(f"Failed to set menu: {e}")

    def set_bounds(self, x, y, width, height):
        if hasattr(self, "hwnd") and self.hwnd:
            try:
                self.adapter.send(
                    {
                        "action": "set_bounds",
                        "x": int(x),
                        "y": int(y),
                        "width": int(width),
                        "height": int(height),
                    }
                )
            except Exception as e:
                self.logger.debug(f"set_bounds not supported by shell: {e}")
        else:
            self._pending_geometry.append(("set_bounds", (x, y, width, height)))

    def set_taskbar_progress(self, value, mode="normal"):
        try:
            self.adapter.send(
                {"action": "set_progress", "value": float(value), "mode": mode}
            )
        except Exception as e:
            self.logger.debug(f"set_taskbar_progress not supported by shell: {e}")

    def toast(self, title, message=""):
        try:
            self.adapter.send(
                {
                    "action": "toast",
                    "title": _to_str(title),
                    "message": _to_str(message),
                }
            )
        except Exception as e:
            self.logger.debug(f"toast not supported by shell: {e}")

    def set_prevent_close(self, prevent=True):
        try:
            self.adapter.send({"action": "prevent_close", "prevent": bool(prevent)})
        except Exception as e:
            self.logger.debug(f"prevent_close not supported by shell: {e}")

    def set_resizable(self, enable):
        try:
            self.adapter.send({"action": "set_resizable", "resizable": bool(enable)})
        except Exception as e:
            self.logger.debug(f"set_resizable not supported by shell: {e}")

    def start(self):
        try:
            if self.adapter.process:
                # Use a loop with timeout to allow for signal processing (like Ctrl+C)
                while self.adapter.process.poll() is None:
                    try:
                        self.adapter.process.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        continue
        except KeyboardInterrupt:
            self.close()
        finally:
            self.logger.info("Chrome Engine stopped.")
