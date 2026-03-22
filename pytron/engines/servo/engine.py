import os
import sys
import json
import logging
import ctypes
import subprocess
import urllib.parse
import threading
import asyncio
import inspect
import pathlib
import time
from typing import Optional, Any, Dict, List
from ...webview import Webview
from .adapter import ServoAdapter
from ...serializer import pytron_serialize

try:
    from ...dependencies import pytron_servo
except ImportError:
    pytron_servo = None


def _to_str(b):
    if isinstance(b, bytes):
        return b.decode("utf-8")
    if hasattr(b, "value") and isinstance(b.value, bytes):  # ctypes.c_char_p
        return b.value.decode("utf-8")
    return str(b)


class ServoBridge:
    """Mocks the native 'lib' DLL interface but redirects to Servo Shell via IPC."""

    def __init__(self, adapter):
        self.adapter = adapter
        self._callbacks = {}
        self.real_hwnd = 0
        self.engine = None
        if pytron_servo:
            self.engine = pytron_servo.ServoEngine()

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
        if self.engine:
            self.engine.show()
        else:
            self.adapter.send({"action": "show"})

    def hide(self, w=None):
        if self.engine:
            self.engine.hide()
        else:
            self.adapter.send({"action": "hide"})

    def set_title(self, title, w=None):
        t = _to_str(title)
        if self.engine:
            self.engine.set_title(t)
        else:
            self.adapter.send({"action": "set_title", "title": t})

    def set_icon(self, icon_path, w=None):
        self.adapter.send({"action": "set_icon", "icon": str(icon_path)})

    def set_size(self, width, height, hints=None, w=None):
        self.adapter.send({"action": "set_size", "width": width, "height": height})

    def navigate(self, url, w=None):
        u = _to_str(url)
        if self.engine:
            self.engine.navigate(u)
        else:
            self.adapter.send({"action": "navigate", "url": u})

    def eval(self, js, w=None):
        self.adapter.send({"action": "eval", "code": _to_str(js)})

    def init_script(self, js, w=None):
        self.adapter.send({"action": "init_script", "js": _to_str(js)})

    def run(self, w=None):
        if self.engine:
            title = self.adapter.config.get("title", "Pytron")
            width = self.adapter.config.get("width", 1024)
            height = self.adapter.config.get("height", 768)
            self.engine.run(title, width, height)
        elif self.adapter.process:
            self.adapter.process.wait()

    def terminate(self, w=None):
        if self.engine:
            self.engine.close()
        else:
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

    def set_fullscreen(self, fullscreen, w=None):
        self.adapter.send({"action": "set_fullscreen", "fullscreen": bool(fullscreen)})

    def set_resizable(self, resizable, w=None):
        self.adapter.send({"action": "set_resizable", "resizable": bool(resizable)})

    def set_always_on_top(self, always_on_top, w=None):
        self.adapter.send(
            {"action": "set_always_on_top", "always_on_top": bool(always_on_top)}
        )

    def dialog_open_file(self, title, default_path, filters):
        self.adapter.send(
            {
                "action": "dialog_open_file",
                "title": _to_str(title),
                "default_path": _to_str(default_path) if default_path else None,
                "filters": _to_str(filters) if filters else None,
            }
        )
        return []

    def dialog_save_file(self, title, default_path, default_name, filters):
        self.adapter.send(
            {
                "action": "dialog_save_file",
                "title": _to_str(title),
                "default_path": _to_str(default_path) if default_path else None,
                "default_name": _to_str(default_name) if default_name else None,
                "filters": _to_str(filters) if filters else None,
            }
        )
        return None

    def dialog_open_folder(self, title, default_path):
        self.adapter.send(
            {
                "action": "dialog_open_folder",
                "title": _to_str(title),
                "default_path": _to_str(default_path) if default_path else None,
            }
        )
        return None

    def get_hwnd(self, w=None):
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


from .forge import ServoForge


class ServoWebView(Webview):
    """
    Electronic ServoNative Engine for Pytron.
    A professional, Servo-based alternative to the native webview.
    """

    def __init__(self, config):
        # 1. Initialize Base (Components, Loops, Infra)
        super().__init__(config)
        self.logger = logging.getLogger("Pytron.ServoWebView")

        # 2. Resolve Servo Binary
        shell_path = config.get("engine_path")
        if not shell_path:
            shell_path = self._resolve_servo_binary(config)

        if not shell_path or not os.path.exists(shell_path):
            self.logger.warning("Servo Engine not found. Auto-provisioning...")
            forge = ServoForge()
            shell_path = forge.provision()

        # 3. Path & URL Setup
        navigate_url = self._routing_comp.normalize_to_pytron(config.get("url", ""))
        self._start_url = navigate_url
        root_path = self._routing_comp.root_path

        # 4. Initialize Bridge & Start Adapter
        self.logger.info(f"Using Servo Shell: {shell_path}")
        self.adapter = ServoAdapter(shell_path, config)
        self.bridge = ServoBridge(self.adapter)
        self.native = self.bridge  # For facade compatibility

        # Connect the engine to the adapter so it can send events
        if self.bridge.engine:
            self.adapter.engine = self.bridge.engine

        self.adapter.start()
        self.adapter.bind_raw(self._handle_ipc_message)

        # 5. Initialize Window & Bindings
        self.w = self.bridge.create(
            config.get("debug", False), self, root_path=root_path
        )

        self._ipc_comp.init_core_bindings()

        self.set_title(config.get("title", "Pytron App"))
        w, h = config.get("dimensions", [800, 600])
        self.set_size(w, h)

        if not config.get("start_hidden", False):
            self.show()

        # 6. Navigate
        self.navigate(navigate_url)

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

        # 8. Event Loop (Asyncio)
        self.loop = asyncio.new_event_loop()

        def start_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        t = threading.Thread(target=start_loop, daemon=True)
        t.start()

        # Force Resizable Update (Fix gray maximize button)
        # Sometimes init flag is overridden by window style defaults in Electron
        self.bridge.adapter.send({"action": "set_resizable", "resizable": True})

    @property
    def hwnd(self):
        """Override to return Electron HWND instead of native engine HWND."""
        if hasattr(self.bridge, "real_hwnd"):
            return self.bridge.real_hwnd
        return 0

    def _handle_ipc_message(self, msg):
        msg_type = msg.get("type")
        payload = msg.get("payload")

        # DEBUG: Log all lifecycle events to trace HWND
        if msg_type == "lifecycle":
            self.logger.info(f"Servo Lifecycle Event: {payload}")

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

                def _respond(status, result):
                    safe_obj = pytron_serialize(result, None)
                    serialized_json = json.dumps(safe_obj)
                    if seq:
                        self.bridge.webview_return(
                            self.w, seq.encode("utf-8"), status, serialized_json
                        )

                def _runner():
                    try:
                        res = func(*args) if isinstance(args, list) else func(args)
                        _respond(0, res)
                    except Exception as e:
                        self.logger.error(f"ServoNative IPC Error in {event}: {e}")
                        _respond(1, str(e))

                async def _async_runner():
                    try:
                        res = func(*args) if isinstance(args, list) else func(args)
                        if inspect.iscoroutine(res):
                            res = await res
                        _respond(0, res)
                    except Exception as e:
                        self.logger.error(
                            f"ServoNative Async IPC Error in {event}: {e}"
                        )
                        _respond(1, str(e))

                if inspect.iscoroutinefunction(func):
                    asyncio.run_coroutine_threadsafe(_async_runner(), self.loop)
                else:
                    self.thread_pool.submit(_runner)

    def bind(self, name, func, run_in_thread=True, secure=False):
        self._bound_functions[name] = func
        self.bridge.webview_bind(self.w, name.encode("utf-8"), None, None)

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
        self.bridge.webview_set_icon(self.w, icon_path)

    def minimize(self):
        self.bridge.adapter.send({"action": "minimize"})

    def maximize(self):
        self.bridge.adapter.send({"action": "maximize"})

    def restore(self):
        self.bridge.adapter.send({"action": "restore"})

    def unmaximize(self):
        self.bridge.adapter.send({"action": "unmaximize"})

    def show(self):
        self.bridge.webview_show(self.w)

    def hide(self):
        self.bridge.webview_hide(self.w)

    def close(self, force=False):
        self.bridge.webview_destroy(self.w)

    def set_title(self, title):
        self.bridge.webview_set_title(self.w, title.encode("utf-8"))

    def set_size(self, w, h):
        self.bridge.webview_set_size(self.w, w, h, 0)

    def navigate(self, url):
        self.bridge.webview_navigate(self.w, url.encode("utf-8"))

    def eval(self, js):
        self.bridge.webview_eval(self.w, js)

    def reload(self):
        self.eval("location.reload()")

    def toggle_maximize(self):
        self.bridge.adapter.send({"action": "toggle_maximize"})

    def set_fullscreen(self, enable):
        self.bridge.webview_set_fullscreen(self.w, enable)

    def set_resizable(self, enable):
        self.bridge.webview_set_resizable(self.w, enable)

    def set_always_on_top(self, enable):
        self.bridge.webview_set_always_on_top(self.w, enable)

    def make_frameless(self):
        self.bridge.adapter.send({"action": "set_frameless", "frameless": True})

    def start_drag(self):
        self.bridge.adapter.send({"action": "start_drag"})

    def set_menu(self, menu_bar):
        # TODO: Implement native menu support for Servo
        pass

    def emit(self, event, data=None):
        payload = json.dumps(data)
        js = f"window.dispatchEvent(new CustomEvent('{event}', {{ detail: {payload} }}));"
        self.eval(js)

    def _sync_state(self):
        if self.app:
            return self.app.state.to_dict()
        return {}

    # --- Dialogs ---
    def dialog_open_file(self, *args, **kwargs):
        title = kwargs.get("title", "Open File")
        default_path = kwargs.get("default_path")
        file_types = kwargs.get("file_types")
        filters_str = None
        if file_types:
            parts = []
            for name, pat in file_types:
                exts = pat.replace("*.", "").replace(";", ",")
                parts.append(f"{name}:{exts}")
            filters_str = ";".join(parts)
        return self.bridge.webview_dialog_open_file(title, default_path, filters_str)

    def dialog_save_file(self, *args, **kwargs):
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
        return self.bridge.webview_dialog_save_file(
            title, default_path, default_name, filters_str
        )

    def dialog_open_folder(self, *args, **kwargs):
        title = kwargs.get("title", "Select Folder")
        default_path = kwargs.get("default_path")
        return self.bridge.webview_dialog_open_folder(title, default_path)

    def set_taskbar_progress(self, state="normal", value=0, max_value=100):
        if self._platform and self.hwnd:
            self._platform.set_taskbar_progress(self.hwnd, state, value, max_value)
        else:
            self.bridge.adapter.send(
                {
                    "action": "set_taskbar_progress",
                    "state": state,
                    "value": value,
                    "max": max_value,
                }
            )

    def system_notification(self, title, message, icon=None):
        if self._platform and self.hwnd:
            self._platform.notification(self.hwnd, title, message, icon)
        else:
            self.bridge.adapter.send(
                {"action": "notification", "title": title, "message": message}
            )

    def toast(self, config):
        if self._platform and self.hwnd:
            self._platform.toast(self.hwnd, config)
        else:
            self.bridge.adapter.send({"action": "toast", "config": config})

    def start(self):
        self.logger.info("Starting Servo Engine...")

        # Register Native Event Handlers
        self.bind("pytron_on_close", self._on_close_requested)

        try:
            # Delegate to bridge which handles both .pyd and subprocess
            self.bridge.webview_run(self.w)
        except KeyboardInterrupt:
            self.close()
        finally:
            self.logger.info("Servo Engine stopped.")
            self._running = False
