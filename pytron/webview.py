import sys
import json
import time
import threading
import asyncio
import pathlib
import logging
from typing import Callable, Optional, Any, TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

# Import Webview Components
from .webview_components.ipc import IPCComponent
from .webview_components.routing import RoutingComponent
from .webview_components.assets import AssetComponent
from .webview_components.dialogs import DialogComponent
from .utils import resolve_native_module, resolve_native_bridge
from .exceptions import NativeEngineError

# Initialize Native Engine via Canonical Resolver
pytron_native = resolve_native_module()
if not pytron_native:
    # Final legacy fallback for simple environments
    try:
        from .dependencies import pytron_native
    except ImportError:
        pass

IS_ANDROID = False


# -------------------------------------------------------------------
# Browser wrapper (Native PyO3 Version)
# -------------------------------------------------------------------
class Webview:
    def __init__(self, config: dict):
        if not pytron_native:
            from .utils import get_native_error_details

            details = get_native_error_details()
            ext = ".pyd" if sys.platform == "win32" else ".so"
            raise NativeEngineError(
                f"Pytron Native Engine binary (pytron_native{ext}) is missing or could not be loaded.\n"
                f"Cause: {details}\n"
                "Ensure it is present in 'pytron/dependencies' or your path. "
                "Try running 'pytron engine install native' to build it for your current system."
            )

        self.config = config
        self.logger = logging.getLogger("Pytron.Webview")
        self.id = config.get("id") or str(int(time.time() * 1000))
        self.app = config.get("__app__")

        # 1. Core Component & Loop Setup
        self.native: Any = None
        self._platform: Any = None
        self._hwnd_cache: int = 0
        self._routing_comp: Optional[RoutingComponent] = None
        self._ipc_comp: Optional[IPCComponent] = None
        self._asset_comp: Optional[AssetComponent] = None
        self._dialog_comp: Optional[DialogComponent] = None

        self.thread_pool: Optional["ThreadPoolExecutor"] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._app_root: Optional[pathlib.Path] = None
        self._running: bool = False
        self._start_url: Optional[str] = None
        self._bound_functions: Dict[str, Callable] = {}

        self._setup_core_infra()
        self._setup_components()

        # 2. Native Engine (Optional for Subclasses)
        # We only auto-initialize if we are the base Webview and engine is native
        # Subclasses like ChromeWebView/ServoWebView handle their own initialization
        if type(self) is Webview and config.get("engine", "native") == "native":
            self._init_native_engine(config)
            self._setup_native_window(config)
            self._ipc_comp.init_core_bindings()

    def _setup_core_infra(self):
        """Initializes thread pools and async loops."""
        if getattr(sys, "frozen", False):
            self._app_root = pathlib.Path(sys.executable).parent
            if hasattr(sys, "_MEIPASS"):
                self._app_root = pathlib.Path(sys._MEIPASS)
        else:
            self._app_root = pathlib.Path.cwd()

        if self.app:
            self.thread_pool = self.app.thread_pool
        else:
            from .utils import com_thread_initializer
            from concurrent.futures import ThreadPoolExecutor

            self.thread_pool = ThreadPoolExecutor(
                max_workers=5, initializer=com_thread_initializer
            )

        self.loop = asyncio.new_event_loop()

        def start_loop():
            if self.loop:
                asyncio.set_event_loop(self.loop)
                self.loop.run_forever()

        t = threading.Thread(target=start_loop, daemon=True)
        t.start()
        self._running = False

    def _setup_components(self):
        """Initializes the modular facade components."""
        self._routing_comp = RoutingComponent(self)
        self._ipc_comp = IPCComponent(self)
        self._asset_comp = AssetComponent(self)
        self._dialog_comp = DialogComponent(self)

    def _init_native_engine(self, config):
        """Bootstraps the native Rust (PyO3) engine."""
        if not pytron_native:
            from .utils import get_native_error_details

            details = get_native_error_details()
            ext = ".pyd" if sys.platform == "win32" else ".so"
            raise NativeEngineError(
                f"Pytron Native Engine binary (pytron_native{ext}) is missing or could not be loaded.\n"
                f"Cause: {details}\n"
            )

        orig_wayland = None
        orig_winit = None
        orig_gdk = None
        is_wayland = False

        if sys.platform.startswith("linux"):
            self.logger.warning("Linux Native Engine is still experimental.")
            import os

            # Disable DMA-BUF renderer to fix blank/white screen issues in VMs and XWayland
            if "WEBKIT_DISABLE_DMABUF_RENDERER" not in os.environ:
                os.environ["WEBKIT_DISABLE_DMABUF_RENDERER"] = "1"

            session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
            if session_type == "wayland":
                is_wayland = True
                self.logger.info(
                    "Wayland session detected. Forcing X11 backend temporarily to initialize native webview."
                )
                orig_wayland = os.environ.get("WAYLAND_DISPLAY")
                orig_winit = os.environ.get("WINIT_UNIX_BACKEND")
                orig_gdk = os.environ.get("GDK_BACKEND")

                if "WAYLAND_DISPLAY" in os.environ:
                    del os.environ["WAYLAND_DISPLAY"]
                os.environ["WINIT_UNIX_BACKEND"] = "x11"
                os.environ["GDK_BACKEND"] = "x11"

        raw_url = config.get("url", "")
        debug = config.get("debug", False)
        final_url = self._routing_comp.normalize_to_pytron(raw_url)
        self._start_url = final_url

        try:
            store_instance = (
                self.app.state._store
                if self.app and hasattr(self.app.state, "_store")
                else None
            )
            initial_url = (
                final_url if sys.platform.startswith("linux") else "about:blank"
            )
            w, h = config.get("dimensions", [800, 600])
            self.native = pytron_native.NativeWebview(
                debug,
                initial_url,
                self._routing_comp.root_path if self._routing_comp else "",
                bool(config.get("resizable", True)),
                bool(config.get("frameless", False)),
                store_instance,
                float(w),
                float(h),
            )
        except RuntimeError as e:
            msg = str(e)
            if "0x8007139F" in msg:
                raise NativeEngineError(
                    f"Failed to initialize Native WebView: Conflict with existing WebView2 process (0x8007139F). {msg}"
                ) from e

            if (
                sys.platform.startswith("linux")
                and "window handle kind is not supported" in msg.lower()
            ):
                import os

                session = os.environ.get("XDG_SESSION_TYPE", "unknown")
                winit = os.environ.get("WINIT_UNIX_BACKEND", "not set")
                gdk = os.environ.get("GDK_BACKEND", "not set")
                raise NativeEngineError(
                    f"Failed to initialize Native WebView on Linux. This is likely a Wayland/X11 mismatch.\n"
                    f"Context:\n"
                    f"  XDG_SESSION_TYPE={session}\n"
                    f"  WINIT_UNIX_BACKEND={winit}\n"
                    f"  GDK_BACKEND={gdk}\n"
                    f"Resolution:\n"
                    f"  1) Fallback to the Chrome engine by setting the environment variable: PYTRON_ENGINE=chrome\n"
                    f"  2) Or re-compile Pytron native with Wayland features enabled.\n"
                    f"Original Error: {msg}"
                ) from e

            raise NativeEngineError(f"Failed to initialize Native WebView: {e}") from e
        finally:
            if is_wayland:
                import os

                if orig_wayland is not None:
                    os.environ["WAYLAND_DISPLAY"] = orig_wayland
                else:
                    os.environ.pop("WAYLAND_DISPLAY", None)
                if orig_winit is not None:
                    os.environ["WINIT_UNIX_BACKEND"] = orig_winit
                else:
                    os.environ.pop("WINIT_UNIX_BACKEND", None)
                if orig_gdk is not None:
                    os.environ["GDK_BACKEND"] = orig_gdk
                else:
                    os.environ.pop("GDK_BACKEND", None)

    def _setup_native_window(self, config):
        """Applies window settings and platform helpers for native engine."""
        self._platform = self._init_platform_helper()

        self.set_title(config.get("title", "Pytron App"))

        # Dimensions are now applied natively in NativeWebview::new,
        # so we don't need to manually call set_size here which could break DPI scaling
        # using the raw Win32 SetWindowPos fallback.
        w, h = config.get("dimensions", [800, 600])

        if config.get("start_maximized", False):
            self.native.maximize()

        if (
            sys.platform == "win32"
            and config.get("hide_from_taskbar", False)
            and self._platform
            and self.hwnd
        ):
            try:
                self._platform.set_utility_window(self.hwnd, True)
            except Exception:
                pass

        if not config.get("start_hidden", False):
            self.show()

        self._init_js_bridge()
        self._apply_ui_settings()

        if config.get("background_color") and self._platform:
            self.set_border_color(config.get("background_color"))

        if config.get("vap_mode"):
            self._asset_comp.load_vap_archive(config.get("vap_archive", "app.pytron"))

    def _init_platform_helper(self):
        """Initializes platform-specific helper implementations."""
        try:
            if sys.platform == "win32":
                from .platforms.windows import WindowsImplementation

                return WindowsImplementation()
            elif sys.platform.startswith("linux"):
                from .platforms.linux import LinuxImplementation

                return LinuxImplementation()
            elif sys.platform == "darwin":
                from .platforms.darwin import DarwinImplementation

                return DarwinImplementation()
        except Exception as e:
            self.logger.warning(f"Failed to load platform helpers: {e}")
        return None

    def _init_js_bridge(self):
        """Initializes the window.pytron bridge in the frontend."""
        init_js = f"""
        (function() {{
            window.pytron = window.pytron || {{}};
            window.pytron.is_ready = true;
            window.pytron.id = "{self.id}";

            // Optimized Event Bus Unpacker
            window.addEventListener('pytron:batch', (e) => {{
                const batch = e.detail;
                if (Array.isArray(batch)) {{
                    batch.forEach(([name, data]) => {{
                        window.dispatchEvent(new CustomEvent(name, {{ detail: data }}));
                    }});
                }}
            }});
        }})();
        """
        self.eval(init_js)

    def start(self):
        self.logger.info("Starting Webview Loop...")
        if self.app:
            if self.app.config.get("_pending_close_to_tray"):
                self.app.config.pop("_pending_close_to_tray")
                self.config["close_to_tray"] = True

        self.native.bind("pytron_on_close", self._on_close_requested)

        if self.config.get("close_to_tray", False):
            self.set_prevent_close(True)

        if self.config.get("always_on_top", False):
            self.set_always_on_top(True)
        if self.config.get("fullscreen", False):
            self.set_fullscreen(True)

        if hasattr(self, "_start_url") and self.config.get("navigate_on_init", True):
            self.navigate(self._start_url)

        self._running = True
        try:
            self.native.run()
        finally:
            self._running = False
            if self.app and self in getattr(self.app, "windows", []):
                try:
                    self.app.windows.remove(self)
                except (ValueError, AttributeError):
                    pass

    @property
    def base_url(self) -> str:
        return self._routing_comp.scheme

    @property
    def root_path(self) -> str:
        return self._routing_comp.root_path

    @property
    def hwnd(self):
        if hasattr(self.native, "get_hwnd"):
            res = self.native.get_hwnd()
            if isinstance(res, (int, float)):
                return int(res)
            return 0
        return getattr(self, "_hwnd_cache", 0)

    def is_visible(self):
        if self._platform and self.hwnd:
            return self._platform.is_visible(self.hwnd)
        if hasattr(self.native, "is_visible"):
            return self.native.is_visible()
        return False

    def is_alive(self):
        return getattr(self, "_running", False)

    # --- IPC Facade ---
    def bind(
        self,
        name: str,
        func: Callable,
        run_in_thread: bool = True,
        secure: bool = False,
    ):
        self._ipc_comp.bind(name, func, run_in_thread, secure)

    def expose(self, entity):
        if callable(entity) and not isinstance(entity, type):
            target = entity
            while hasattr(target, "__wrapped__"):
                target = getattr(target, "__wrapped__")
            if hasattr(target, "raw_function"):
                target = getattr(target, "raw_function")
            func_name = getattr(
                target, "__name__", getattr(entity, "__name__", f"exposed_{id(entity)}")
            )
            self.bind(func_name, entity)
            return entity
        if isinstance(entity, type):
            instance = entity()
            for name in dir(instance):
                if not name.startswith("_") and callable(getattr(instance, name)):
                    self.bind(name, getattr(instance, name))
            return entity

    # --- Routing Facade ---
    def navigate(self, url: str):
        if not self._routing_comp or not self.native:
            return
        target = self._routing_comp.normalize_to_pytron(url)
        self.config["url"] = target
        if not getattr(self, "_running", False):
            self._start_url = target
        self.native.navigate(target)
        self._apply_ui_settings()

    def normalize_path(self, config: dict):
        self._routing_comp.normalize_config_url(config)

    # --- Assets Facade ---
    def serve_data(self, key: str, data: bytes, mime_type: str) -> str:
        return self._asset_comp.serve_data(key, data, mime_type)

    def _serve_asset_callback(self, key: str):
        return self._asset_comp.serve_asset_callback(key)

    def _get_binary_asset(self, key: str):
        return self._asset_comp.get_binary_asset(key)

    # --- Dialogs Facade ---
    def dialog_open_file(self, *args, **kwargs):
        return self._dialog_comp.open_file(*args, **kwargs)

    def dialog_save_file(self, *args, **kwargs):
        return self._dialog_comp.save_file(*args, **kwargs)

    def dialog_open_folder(self, *args, **kwargs):
        return self._dialog_comp.open_folder(*args, **kwargs)

    def message_box(self, *args, **kwargs):
        return self._dialog_comp.message_box(*args, **kwargs)

    def set_taskbar_progress(self, state="normal", value=0, max_value=100):
        self._dialog_comp.set_taskbar_progress(state, value, max_value)

    def system_notification(self, title, message, icon=None):
        self._dialog_comp.notification(title, message, icon)

    def toast(self, config):
        self._dialog_comp.toast(config)

    # --- Window Control ---
    def set_title(self, title):
        if self._platform and self.hwnd:
            self._platform.set_title(self.hwnd, title)
            return
        if self.native:
            self.native.set_title(title)

    def set_size(self, w, h):
        if self.native and hasattr(self.native, "set_size"):
            self.native.set_size(w, h, 0)
            return
        if self._platform and self.hwnd:
            self._platform.set_size(self.hwnd, w, h, 0)
            return

    def set_bounds(self, x, y, width, height):
        if self.native and hasattr(self.native, "set_bounds"):
            # Note: native set_bounds on windows now takes more args (no_move, no_size),
            # but Python signature doesn't expose it here. We map to the minimal version if possible,
            # or rely on the platform fallback for complex flags.
            pass

        if self._platform and self.hwnd:
            self._platform.set_bounds(
                self.hwnd, int(x), int(y), int(width), int(height)
            )
            return

        if self.native and hasattr(self.native, "set_size"):
            self.native.set_size(int(width), int(height), 0)

    def center(self, width=None, height=None):
        if self._platform and self.hwnd:
            self._platform.center(self.hwnd, width=width, height=height)
            return
        call_native = getattr(self.native, "center", None)
        if call_native:
            # Native engine's center now supports (width, height)
            if width is not None and height is not None:
                call_native(int(width), int(height))
            else:
                call_native()

    def eval(self, js):
        self.native.eval(js)

    def reload(self):
        self.native.eval("location.reload()")

    def open_devtools(self):
        call_native = getattr(self.native, "open_devtools", None)
        if call_native:
            call_native()
            return True
        self.eval("try { window.__pytron_open_devtools?.(); } catch (e) {}")
        return False

    def close(self, force=False):
        if not force and self.config.get("close_to_tray", False):
            self.hide()
            return
        self.native.terminate()

    def hide(self):
        if self._platform and self.hwnd:
            self._platform.hide(self.hwnd)
            return
        self.native.hide()

    def show(self):
        if self._platform and self.hwnd:
            self._platform.show(self.hwnd)
            return
        self.native.show()

    def set_icon(self, icon_path):
        if self._platform and self.hwnd:
            self._platform.set_window_icon(self.hwnd, icon_path)
            return
        if hasattr(self.native, "set_icon"):
            self.native.set_icon(icon_path)

    def set_menu(self, menu_bar):
        if self._platform and self.hwnd:
            self._platform.set_menu(self.hwnd, menu_bar)
            return
        if hasattr(self.native, "set_menu"):
            self.native.set_menu(menu_bar)

    def minimize(self):
        if self._platform and self.hwnd:
            self._platform.minimize(self.hwnd)
            return
        self.native.minimize()

    def maximize(self):
        if self._platform and self.hwnd:
            self._platform.maximize(self.hwnd)
            return
        self.native.maximize()

    def restore(self):
        if self._platform and self.hwnd:
            self._platform.restore(self.hwnd)
            return
        if hasattr(self.native, "restore"):
            self.native.restore()
        else:
            self.unmaximize()

    def toggle_maximize(self):
        if self._platform and self.hwnd:
            return self._platform.toggle_maximize(self.hwnd)
        self.maximize()

    def unmaximize(self):
        if hasattr(self.native, "unmaximize"):
            self.native.unmaximize()

    def set_fullscreen(self, enable):
        if self._platform and self.hwnd:
            self._platform.set_fullscreen(self.hwnd, enable)
            return
        self.native.set_fullscreen(enable)

    def set_always_on_top(self, enable):
        if self._platform and self.hwnd:
            self._platform.set_always_on_top(self.hwnd, enable)
            return
        call_native = getattr(self.native, "set_always_on_top", None)
        if call_native:
            call_native(enable)

    def set_resizable(self, enable):
        call_native = getattr(self.native, "set_resizable", None)
        if call_native:
            call_native(enable)

    def start_drag(self):
        if self._platform and self.hwnd:
            self._platform.start_drag(self.hwnd)
            return
        self.native.start_drag()

    def set_prevent_close(self, prevent):
        if hasattr(self.native, "set_prevent_close"):
            self.native.set_prevent_close(prevent)

    def set_border_color(self, color_hex):
        if self._platform:
            self._platform.set_border_color(self.hwnd, color_hex)

    def set_slim_titlebar(self, enable=True):
        if hasattr(self.native, "set_decorations"):
            self.native.set_decorations(not enable)

    def get_registered_shortcuts(self):
        if self.app and hasattr(self.app, "shortcuts"):
            if hasattr(self.app.shortcuts, "shortcuts"):
                return list(self.app.shortcuts.shortcuts.keys())
        return []

    def emit(self, event, data=None):
        payload = json.dumps(data)
        js = f"window.dispatchEvent(new CustomEvent('{event}', {{ detail: {payload} }}));"
        self.eval(js)

    def dispatch(self, event_name: str, data: Any = None):
        """
        High-performance dispatch alias for emit.
        Used by the App-level Event Bus batching system.
        """
        return self.emit(event_name, data)

    def _apply_ui_settings(self):
        js = []
        if self.config.get("default_context_menu") is False:
            js.append(
                "try { document.addEventListener('contextmenu', e => e.preventDefault()); } catch(e) {}"
            )
        if js:
            full_script = (
                "(function(){ setTimeout(() => { " + " ".join(js) + " }, 100); })();"
            )
            self.eval(full_script)

    def _on_close_requested(self):
        if self.config.get("close_to_tray", False) or getattr(
            self, "_is_utility", False
        ):
            self.hide()
        else:
            self.native.terminate()
