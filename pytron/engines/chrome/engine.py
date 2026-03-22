import os
import sys
import json
import logging
import ctypes
import subprocess
import urllib.parse
from typing import Optional, List, Any
from ...webview import Webview
from .adapter import ChromeAdapter
from ...serializer import pytron_serialize


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
                },
            }
        )
        return 1

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
        except:
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
        except:
            pass


from .forge import ChromeForge


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

        self.adapter.start()
        self.adapter.bind_raw(self._handle_ipc_message)

        # 5. Initialize Window & Bindings
        self.w = self.bridge.create(
            config.get("debug", False), self, root_path=root_path
        )

        self._ipc_comp.init_core_bindings()

        self.set_title(config.get("title", "Pytron App"))
        self._setup_icon(config)

        w, h = config.get("dimensions", [800, 600])
        self.set_size(w, h)

        if not config.get("start_hidden", False):
            self.show()

        # 6. Navigate
        self.navigate(navigate_url)

    def _setup_icon(self, config):
        """Resolves and sets the window icon."""
        icon_raw = config.get("icon")
        if icon_raw:
            if os.path.exists(icon_raw):
                config["icon"] = os.path.abspath(icon_raw)
            else:
                possible = os.path.join(self._routing_comp.root_path, icon_raw)
                if os.path.exists(possible):
                    config["icon"] = os.path.abspath(possible)

        if config.get("icon"):
            self.set_icon(config["icon"])

    def _resolve_chrome_binary(self, config) -> Optional[str]:
        """Chrome-specific binary detection logic."""
        renamed_engine = None
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

        # 7. JS Init Shim (With Proxy for Dynamic Methods)
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
            window.pytron_drag = () => window.__pytron_native_bridge('pytron_drag', []);
            window.pytron_minimize = () => window.__pytron_native_bridge('pytron_minimize', []);
            window.pytron_get_asset = (key) => window.__pytron_native_bridge('pytron_get_asset', [key]);
            
            window['pytron_drag'] = window.pytron_drag;
            window['pytron_minimize'] = window.pytron_minimize;
            window['pytron_get_asset'] = window.pytron_get_asset;
            window['__pytron_vap_get'] = window.pytron_get_asset; 

        }})();
        """
        self.eval(init_js)

        # Force Resizable Update (Fix gray maximize button)
        # Sometimes init flag is overridden by window style defaults in Electron
        self.adapter.send({"action": "set_resizable", "resizable": True})

    @property
    def hwnd(self):
        """Override to return Electron HWND instead of native engine HWND."""
        if hasattr(self.bridge, "real_hwnd"):
            return self.bridge.real_hwnd
        return 0

    def _handle_ipc_message(self, msg):
        import inspect
        import asyncio

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
            except:
                pass
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

            if event in self._bound_functions:
                func = self._bound_functions[event]
                try:
                    result = func(*args) if isinstance(args, list) else func(args)

                    if inspect.iscoroutine(result):
                        try:
                            result = asyncio.run(result)
                        except RuntimeError:
                            pass

                    safe_obj = pytron_serialize(result, None)
                    serialized_json = json.dumps(safe_obj)

                    if seq:
                        self.bridge.return_result(seq, 0, serialized_json)
                except Exception as e:
                    self.logger.error(f"Mojo IPC Error in {event}: {e}")
                    if seq:
                        safe_err = pytron_serialize(str(e), None)
                        self.bridge.return_result(seq, 1, json.dumps(safe_err))

    def bind(self, name, func, run_in_thread=True, secure=False):
        self._bound_functions[name] = func
        self.bridge.bind(name, None, None)

    # --- Feature Overrides (Compatibility Layer) ---

    def center(self):
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

    def show(self):
        self.bridge.show()

    def hide(self):
        self.bridge.hide()

    def close(self, force=False):
        self.bridge.terminate()

    def set_title(self, title):
        self.bridge.set_title(title)

    def set_size(self, w, h):
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
