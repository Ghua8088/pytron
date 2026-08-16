import json
import inspect
import asyncio
from typing import Any, Callable
from .base import WebviewComponent
from ..serializer import pytron_serialize
from ..utils import com_thread_initializer


class IPCComponent(WebviewComponent):
    """Handles IPC bindings, callbacks, and state synchronization."""

    def __init__(self, webview: Any):
        super().__init__(webview)
        self._bound_functions = {}
        self._spammy_methods = {
            "pytron_serve_asset",
            "__pytron_vap_get",
        }

    def bind(
        self,
        name: str,
        python_func: Callable,
        run_in_thread: bool = True,
        secure: bool = False,
    ):
        """Registers a Python function to be callable from JavaScript."""
        is_async = inspect.iscoroutinefunction(python_func)
        self._bound_functions[name] = python_func

        # The Wrapper that Rust/Mojo calls: (seq, args_json, ptr) or (seq, args_list)
        def _native_callback(seq, req=None, arg_ptr=None, *extra):
            try:
                if isinstance(req, (list, dict)):
                    # Chrome/Servo Path: req is already a list of decoded Python objects
                    args = req
                elif req is not None:
                    # Native Path: req is a JSON string
                    args = json.loads(req)
                else:
                    args = []
            except Exception:
                args = []

            # Internal logging
            if not name.startswith("inspector_") and name not in self._spammy_methods:
                self.logger.debug(f"IPC Call: {name}({args})")

            # Result serializer
            def _serialize_result(res):
                return pytron_serialize(res, vap_provider=self.webview.serve_data)

            # Response Helper
            def _respond(status, result):
                res_str = json.dumps(result)
                if self.native:
                    self.native.return_result(seq, status, res_str)

            # Runner Logic
            def _runner():
                com_thread_initializer()
                try:
                    target_func = python_func
                    # Fallback lookup in case function reference was updated on App
                    if not target_func:
                        app = getattr(
                            self.webview, "app", None
                        ) or self.webview.config.get("__app__")
                        if (
                            app
                            and hasattr(app, "_exposed_functions")
                            and name in app._exposed_functions
                        ):
                            target_func = app._exposed_functions[name]["func"]

                    res = target_func(*args)
                    _respond(0, _serialize_result(res))
                except Exception as e:
                    import traceback

                    err_type = type(e).__name__
                    err_msg = str(e)
                    stack = traceback.format_exc()

                    # LOUD terminal logging for backend errors
                    print("\n" + "=" * 60)
                    print(f"❌ PYTRON BACKEND ERROR: {name}")
                    print("-" * 60)
                    print(stack.strip())
                    print("=" * 60 + "\n")

                    error_payload = {
                        "pytron_error": True,
                        "type": err_type,
                        "message": err_msg,
                        "traceback": (
                            stack if self.webview.config.get("debug") else None
                        ),
                        "function": name,
                    }
                    _respond(1, error_payload)

            async def _async_runner():
                try:
                    res = await python_func(*args)
                    _respond(0, _serialize_result(res))
                except Exception as e:
                    import traceback

                    err_type = type(e).__name__
                    err_msg = str(e)
                    stack = traceback.format_exc()

                    print("\n" + "!" * 60)
                    print(f"❌ PYTRON ASYNC ERROR: {name}")
                    print("-" * 60)
                    print(stack.strip())
                    print("!" * 60 + "\n")

                    error_payload = {
                        "pytron_error": True,
                        "type": err_type,
                        "message": err_msg,
                        "traceback": (
                            stack if self.webview.config.get("debug") else None
                        ),
                        "function": name,
                    }
                    _respond(1, error_payload)

            if is_async:
                asyncio.run_coroutine_threadsafe(_async_runner(), self.webview.loop)
            else:
                if run_in_thread:
                    self.webview.thread_pool.submit(_runner)
                else:
                    _runner()

        # Register with Native Engine
        if self.native:
            self.native.bind(name, _native_callback)

    def init_core_bindings(self):
        """Registers all standard Pytron system APIs."""
        wv = self.webview

        # 1. CORE SYSTEM BINDINGS
        self.bind("pytron_set_title", wv.set_title, run_in_thread=False)
        self.bind("pytron_set_size", wv.set_size, run_in_thread=False)
        self.bind("pytron_close", wv.close, run_in_thread=False)
        self.bind("pytron_reload", wv.reload, run_in_thread=False)
        self.bind("pytron_open_devtools", wv.open_devtools, run_in_thread=False)
        self.bind("pytron_toggle_maximize", wv.toggle_maximize, run_in_thread=False)
        self.bind("pytron_hide", wv.hide, run_in_thread=False)
        self.bind("pytron_show", wv.show, run_in_thread=False)
        self.bind("pytron_minimize", wv.minimize, run_in_thread=False)
        self.bind("pytron_maximize", wv.maximize, run_in_thread=False)
        self.bind("pytron_center", wv.center, run_in_thread=False)
        self.bind("pytron_sync_state", self._sync_state, run_in_thread=False)
        self.bind("pytron_log", lambda msg: print(f"[JS] {msg}"), run_in_thread=False)

        # Internal Assets
        self.bind("__pytron_vap_get", wv._get_binary_asset, run_in_thread=True)
        if self.native:
            self.native.bind("pytron_serve_asset", wv._serve_asset_callback)

        self.bind("pytron_set_slim_titlebar", wv.set_slim_titlebar, run_in_thread=False)
        self.bind("pytron_set_bounds", wv.set_bounds, run_in_thread=False)
        self.bind(
            "pytron_get_registered_shortcuts",
            wv.get_registered_shortcuts,
            run_in_thread=True,
        )
        self.bind("pytron_set_border_color", wv.set_border_color, run_in_thread=False)

        # 2. SYSTEM TOOLING / DIALOGS
        self.bind("pytron_dialog_open_file", wv.dialog_open_file, run_in_thread=True)
        self.bind("pytron_dialog_save_file", wv.dialog_save_file, run_in_thread=True)
        self.bind(
            "pytron_dialog_open_folder", wv.dialog_open_folder, run_in_thread=True
        )
        self.bind("pytron_message_box", wv.message_box, run_in_thread=True)
        self.bind(
            "pytron_system_notification", wv.system_notification, run_in_thread=True
        )
        self.bind(
            "pytron_set_taskbar_progress", wv.set_taskbar_progress, run_in_thread=True
        )
        self.bind("pytron_toast", wv.toast, run_in_thread=True)

        # 3. CLEAN ALIASES
        self.bind("close", wv.close, run_in_thread=False)
        self.bind("hide", wv.hide, run_in_thread=False)
        self.bind("show", wv.show, run_in_thread=False)
        self.bind("minimize", wv.minimize, run_in_thread=False)
        self.bind("maximize", wv.maximize, run_in_thread=False)
        self.bind("center", wv.center, run_in_thread=False)
        self.bind("reload", wv.reload, run_in_thread=False)
        self.bind("open_devtools", wv.open_devtools, run_in_thread=False)
        self.bind("toggle_maximize", wv.toggle_maximize, run_in_thread=False)
        self.bind("set_title", wv.set_title, run_in_thread=False)
        self.bind("set_size", wv.set_size, run_in_thread=False)
        self.bind("set_slim_titlebar", wv.set_slim_titlebar, run_in_thread=False)
        self.bind("dialog_open_file", wv.dialog_open_file, run_in_thread=True)
        self.bind("dialog_save_file", wv.dialog_save_file, run_in_thread=True)
        self.bind("dialog_open_folder", wv.dialog_open_folder, run_in_thread=True)
        self.bind("open_folder", wv.dialog_open_folder, run_in_thread=True)
        self.bind("message_box", wv.message_box, run_in_thread=True)
        self.bind("system_notification", wv.system_notification, run_in_thread=True)
        self.bind("toast", wv.toast, run_in_thread=True)
        self.bind("set_taskbar_progress", wv.set_taskbar_progress, run_in_thread=True)
        self.bind("set_bounds", wv.set_bounds, run_in_thread=False)
        self.bind("set_border_color", wv.set_border_color, run_in_thread=False)
        self.bind(
            "get_registered_shortcuts", wv.get_registered_shortcuts, run_in_thread=True
        )

    def _sync_state(self):
        """Synchronizes the application reactive state with the frontend."""
        from ..state import log_shield

        app = getattr(self.webview, "app", None)
        if app:
            try:
                if self.webview.config.get("debug"):
                    log_shield("Received pytron_sync_state Request")
                state_dict = app.state.to_dict()
                return state_dict
            except Exception as e:
                log_shield(f"SYNC FATAL ERROR: {e}")
                return {}
        else:
            log_shield("SYNC ERROR: No App Instance in Webview")
            return {}
