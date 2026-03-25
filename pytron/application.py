import os
import sys
import asyncio
from typing import Any, List, Optional, Dict, Callable
from concurrent.futures import ThreadPoolExecutor

from .state import ReactiveState
from .router import Router
from .shortcuts import ShortcutManager
from .inspector import Inspector
import inspect

# Component Imports
from .apputils.codegen import CodegenComponent
from .apputils.native import NativeComponent
from .apputils.config import ConfigComponent
from .apputils.window_mixin import WindowComponent
from .apputils.extras import ExtrasComponent
from .apputils.shell import ShellComponent
from .apputils.plugins import PluginComponent
from .apputils.reporter import CrashReporter


class App:
    def __init__(self, config_file="settings.json"):
        # Initialize Components
        self._config_comp = ConfigComponent(self)
        self._window_comp = WindowComponent(self)
        self._extras_comp = ExtrasComponent(self)
        self._codegen_comp = CodegenComponent(self)
        self._native_comp = NativeComponent(self)
        self._shell_comp = ShellComponent(self)
        self._plugin_comp = PluginComponent(self)
        self._crash_comp = CrashReporter(self)

        from .utils import com_thread_initializer

        env_engine = os.environ.get("PYTRON_ENGINE")
        engine_explicit = env_engine is not None

        # Engine Selection (PRO FEATURES) - MUST HAPPEN FIRST for Schism protection
        self.engine = env_engine or (
            "chrome" if sys.platform.startswith("linux") else "native"
        )
        os.environ["PYTRON_ENGINE"] = self.engine

        # PERFORMANCE: Shared thread pool for all internal window operations
        initializer = __import__(
            "pytron.utils", fromlist=["com_thread_initializer"]
        ).com_thread_initializer
        self.thread_pool = ThreadPoolExecutor(max_workers=10, initializer=initializer)

        # Init State
        self.windows: List[Any] = []
        self.is_running: bool = False
        self._exposed_functions: Dict[str, Callable] = {}
        self._exposed_ts_defs: Dict[str, str] = {}
        self._pydantic_models: Dict[str, Any] = {}
        self.shortcuts: Dict[str, Any] = {}
        self.plugins: List[Any] = []
        self._on_exit_callbacks: List[Callable] = []
        self.tray: Any = None
        self.shortcut_manager = ShortcutManager()
        self._on_file_drop_callback: Optional[Callable] = None
        self.app_root: str = ""
        from collections import defaultdict

        self._event_listeners: Dict[str, List[Callable]] = defaultdict(list)

        # Explicit Attribute Declarations for IDE Support
        self.config: dict = {}
        self.logger: Any = None
        self.storage_path: str = ""

        # Router Init
        self.router = Router()

        # Event Loop (Asyncio) - Shared for core async tasks
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        # ConfigComponent setup
        self._config_comp._setup_logging()
        self.router.logger = self.logger  # Share logger

        from .state import log_shield

        log_shield(f"App __init__ called. Frozen={getattr(sys, 'frozen', False)}")

        self.state = ReactiveState(self)

        self._config_comp._check_deep_link()
        self._config_comp._load_config(config_file)
        _, safe_title = self._config_comp._setup_identity()
        self._config_comp._setup_storage(safe_title)
        self._crash_comp.setup()
        self._config_comp._resolve_resources()
        self._register_core_apis()

        # Update engine based on config or CLI flags if they override the initial detection
        config_engine = self.config.get("engine")
        cli_engine_explicit = "--web" in sys.argv or "--engine" in sys.argv
        if config_engine and not engine_explicit and not cli_engine_explicit:
            self.engine = config_engine
            os.environ["PYTRON_ENGINE"] = self.engine

        # Override via CLI flags if present
        if "--web" in sys.argv:
            self.engine = "chrome"
            os.environ["PYTRON_ENGINE"] = "chrome"

        for i, arg in enumerate(sys.argv):
            if arg == "--engine" and i + 1 < len(sys.argv):
                self.engine = sys.argv[i + 1]
                os.environ["PYTRON_ENGINE"] = self.engine

        if self.engine == "servo":
            self.logger.warning(
                "Servo engine is disabled in this release train. Falling back to Chrome."
            )
            self.engine = "chrome"
            os.environ["PYTRON_ENGINE"] = "chrome"

        if self.engine == "chrome":
            self.logger.info("Using Chrome Shell Engine (Mojo IPC)")

        # Initialize Inspector
        self.inspector = Inspector(self)

        if self.config.get("single_instance", False):
            # ConfigMixin already handles this via _setup_identity -> _setup_single_instance
            pass

        self._config_comp._setup_key_value_store()

        # Register automatic cleanup for thread pool
        # Register automatic cleanup for thread pool
        @self.on_exit
        def _cleanup_pool():
            if self.thread_pool:
                self.logger.debug("Shutting down thread pool...")
                try:
                    self.thread_pool.shutdown(wait=False, cancel_futures=True)
                except Exception as e:
                    self.logger.debug(f"Error shutting down thread pool: {e}")
                self.thread_pool = None

            # Register Inspector Shortcuts
            self.logger.debug("Registering Inspector shortcuts (F12, Ctrl+Shift+I)")
            # F12 often fails on Windows due to system/kernel debugger reservations
            self.shortcut("F12", self.toggle_inspector)
            self.shortcut("Ctrl+Shift+I", self.toggle_inspector)

            # Additional fallback
            self.shortcut("Shift+F12", self.toggle_inspector)

            # Expose to JS for manual triggering if needed
            self.expose(self.toggle_inspector, name="inspector_toggle")

        # Load Plugins
        self._plugin_comp.discover_and_load()

        # Build Optimized Dispatcher (Buffered)
        from collections import deque

        self._dispatch_buffer = deque()
        self.loop.create_task(self._flush_events_task())

        # AUTO-CODEGEN: Generate TypeScript definitions in debug mode (After plugins are loaded)
        if self.config.get("debug", False):
            try:
                self.generate_types()
            except Exception as e:
                self.logger.debug(f"Codegen failed: {e}")

    # --- Config Component Forwarding ---
    def store_set(self, key: str, value: Any):
        """Sets a value in the persistent store."""
        return self._config_comp.store_set(key, value)

    def store_get(self, key: str, default: Any = None) -> Any:
        """Gets a value from the persistent store."""
        return self._config_comp.store_get(key, default)

    def store_delete(self, key: str) -> bool:
        """Removes a key from the persistent store."""
        return self._config_comp.store_delete(key)

    # --- Window Component Forwarding ---
    def create_window(self, **kwargs) -> Any:
        """Creates a new application window."""
        return self._window_comp.create_window(**kwargs)

    def run(self, **kwargs):
        """Starts the application event loop and shows the main window."""
        return self._window_comp.run(**kwargs)

    def register_protocol(self, scheme: str = "pytron"):
        """Registers a custom URL protocol for the application."""
        return self._window_comp.register_protocol(scheme)

    def broadcast(self, event_name: str, data: Any):
        """Sends an event to all open windows."""
        return self._window_comp.broadcast(event_name, data)

    def emit_to(self, window_id: str, event_name: str, data: Any) -> bool:
        """Send an event to a specific window by its ID."""
        return self._window_comp.emit_to(window_id, event_name, data)

    def get_window(self, window_id: str) -> Any:
        """Find a window by its ID."""
        return self._window_comp.get_window(window_id)

    def emit(self, event_name: str, data: Any):
        """Alias for broadcast."""
        return self._window_comp.emit(event_name, data)

    def hide(self):
        """Hides all application windows."""
        return self._window_comp.hide()

    def show(self):
        """Shows all application windows."""
        return self._window_comp.show()

    def notify(
        self, title: str, message: str, type: str = "info", duration: int = 5000
    ):
        """Shows a notification in all windows."""
        return self._window_comp.notify(title, message, type, duration)

    def quit(self):
        """Quits the application."""
        return self._window_comp.quit()

    def set_menubar(self, menu_bar: Any):
        """Sets the menu bar for the primary window."""
        return self._window_comp.set_menubar(menu_bar)

    @property
    def is_visible(self) -> bool:
        """Returns True if the primary window is visible."""
        return self._window_comp.is_visible

    # --- Extras Component Forwarding ---
    def load_plugin(self, manifest_path: str):
        """Loads a plugin from the specified manifest path."""
        return self._extras_comp.load_plugin(manifest_path)

    def setup_tray(self, title: str = None, icon: str = None) -> Any:
        """Initializes the system tray icon."""
        return self._extras_comp.setup_tray(title, icon)

    def setup_tray_standard(self, title: str = None, icon: str = None) -> Any:
        """Initializes a standard system tray with Show/Hide/Quit items."""
        return self._extras_comp.setup_tray_standard(title, icon)

    # --- Codegen Component Forwarding ---
    def generate_types(self, output_path: str = "frontend/src/pytron.d.ts"):
        """Generates TypeScript definitions for all exposed functions."""
        return self._codegen_comp.generate_types(output_path)

    # --- Native Component Forwarding ---
    def set_start_on_boot(self, enable: bool = True) -> bool:
        """Enables or disables automatic application startup on system boot."""
        return self._native_comp.set_start_on_boot(enable)

    def message_box(self, title: str, message: str, style: int = 0) -> int:
        """Shows a native message box."""
        return self._native_comp.message_box(title, message, style)

    def dialog_save_file(
        self, title="Save File", default_path=None, default_name=None, file_types=None
    ):
        """Opens a native save file dialog."""
        return self._native_comp.dialog_save_file(
            title, default_path, default_name, file_types
        )

    def dialog_open_file(self, title="Open File", default_path=None, file_types=None):
        """Opens a native file selection dialog."""
        return self._native_comp.dialog_open_file(title, default_path, file_types)

    def dialog_open_folder(self, title="Select Folder", default_path=None):
        """Opens a native folder selection dialog."""
        return self._native_comp.dialog_open_folder(title, default_path)

    # --- Aliases for Backward Compatibility ---
    open_file_dialog = dialog_open_file
    save_file_dialog = dialog_save_file
    open_folder_dialog = dialog_open_folder

    def system_notification(self, title: str = None, message: str = ""):
        """Sends a system-level notification via the OS."""
        return self._native_comp.system_notification(title, message)

    def show_toast(self, config: dict):
        """Sends a rich, modern system notification."""
        return self._native_comp.show_toast(config)

    def copy_to_clipboard(self, text: str) -> bool:
        """Copies text to the system clipboard."""
        return self._native_comp.copy_to_clipboard(text)

    def get_clipboard_text(self) -> str:
        """Returns text from the system clipboard."""
        return self._native_comp.get_clipboard_text()

    def get_system_info(self) -> dict:
        """Returns hardware and OS information."""
        return self._native_comp.get_system_info()

    def set_window_curvature(self, preference: Any = None):
        """Forces rounded or square corners on Windows 11."""
        return self._native_comp.set_window_curvature(preference)

    def set_border_color(self, color_hex: str):
        """Sets the window border color on supported platforms."""
        return self._native_comp.set_border_color(color_hex)

    def set_background_material(self, material: str = "mica"):
        """
        Sets the window background material (Windows 11).
        Options: 'mica', 'acrylic', 'tabbed', 'none'
        """
        return self._native_comp.set_background_material(material)

    def set_mica_effect(self, enable: bool = True):
        """Helper to enable/disable Mica effect on Windows 11."""
        return self.set_background_material("mica" if enable else "none")

    # --- Shell Component Forwarding ---
    def open_external(self, url: str):
        """Opens a URL or file path in the default system browser/handler."""
        return self._shell_comp.open_external(url)

    def show_item_in_folder(self, path: str):
        """Opens the folder containing the file and selects it."""
        return self._shell_comp.show_item_in_folder(path)

    def trash_item(self, path: str) -> bool:
        """Moves a file to the system trash/recycle bin."""
        return self._shell_comp.trash_item(path)

    def get_base_url(self) -> str:
        """Returns the base URL for the current platform and engine."""
        # 1. If a window exists, it is the authority on the current scheme
        if self.windows:
            return self.windows[0].base_url

        # 2. Fallback to detection logic
        # Chrome Engine (Electron) always uses pytron://
        if getattr(self, "engine", "native") == "chrome":
            return "pytron://localhost"

        # Native Engine (WebView2) requires https:// on Windows
        if sys.platform == "win32":
            return "https://pytron.localhost"
        return "pytron://localhost"

    def on_exit(self, func):
        """
        Register a function to run when the application is exiting.
        Can be used as a decorator: @app.on_exit
        """
        self._on_exit_callbacks.append(func)
        return func

    # Expose function to all windows
    def expose(self, func=None, name=None, secure=False, run_in_thread=True):
        """
        Expose a function to ALL windows created by this App.
        Can be used as a decorator: @app.expose or @app.expose(secure=True)
        """
        # Case 1: Used as @app.expose(secure=True) - func is None
        if func is None:

            def decorator(f):
                self.expose(f, name=name, secure=secure, run_in_thread=run_in_thread)
                return f

            return decorator

        # Case 2: Used as @app.expose or app.expose(func)
        # If the user passed a class or an object (bridge), expose its public callables
        if isinstance(func, type) or (not callable(func) and hasattr(func, "__dict__")):
            # Try to instantiate the class if a class was provided, otherwise use the instance
            bridge = None
            if isinstance(func, type):
                try:
                    bridge = func()
                except Exception:
                    # Could not instantiate; fall back to using the class object itself
                    bridge = func
            else:
                bridge = func

            for attr_name in dir(bridge):
                if attr_name.startswith("_"):
                    continue
                try:
                    attr = getattr(bridge, attr_name)
                except Exception:
                    continue
                if callable(attr):
                    try:
                        # For classes, we assume default security unless specified?
                        # Or maybe we shouldn't support granular security on class-based expose yet
                        # for simplicity
                        # just pass 'secure' to all methods.
                        self._exposed_functions[attr_name] = {
                            "func": attr,
                            "secure": secure,
                            "run_in_thread": run_in_thread,
                        }
                        self._exposed_ts_defs[attr_name] = (
                            self._codegen_comp._get_ts_definition(attr_name, attr)
                        )
                    except Exception:
                        pass
            return func

        if name is None:
            if hasattr(func, "__name__"):
                name = func.__name__
            elif hasattr(func, "func") and hasattr(
                getattr(func, "func"), "__name__"
            ):  # partials
                name = getattr(func, "func").__name__
            else:
                name = f"exposed_{id(func)}"

        self._exposed_functions[name] = {
            "func": func,
            "secure": secure,
            "run_in_thread": run_in_thread,
        }
        self._exposed_ts_defs[name] = self._codegen_comp._get_ts_definition(name, func)
        return func

    def shortcut(self, key_combo, func=None):
        """
        Register a global keyboard shortcut for all windows.
        Example: @app.shortcut('Ctrl+Q')
        """
        if func is None:

            def decorator(f):
                self.shortcut(key_combo, f)
                return f

            return decorator
        self.shortcuts[key_combo] = func
        return func

    def on_deep_link(self, pattern: str):
        """
        Decorator to register a handler for deep links.
        Pattern examples: "project/{id}", "settings", "oauth/callback"

        @app.on_deep_link("project/{id}")
        def open_project(id, link):
            print(f"Opening project {id} from {link.raw_url}")
        """
        return self.router.route(pattern)

    def on_file_drop(self, func):
        """
        Decorator to register a handler for file drop events.

        @app.on_file_drop
        def handle_drop(window, files):
            print(f"Dropped files on window {window.id}: {files}")
        """
        self._on_file_drop_callback = func
        return func

    def _register_core_apis(self):
        """Automatically exposes built-in system APIs to the frontend."""

        # --- Event Bus Bridge ---
        def _handle_frontend_event(name, data=None):
            if name in self._event_listeners:
                for cb in self._event_listeners[name]:
                    try:
                        if inspect.iscoroutinefunction(cb):
                            asyncio.run_coroutine_threadsafe(cb(data), self.loop)
                        else:
                            self.thread_pool.submit(cb, data)
                    except Exception as e:
                        self.logger.error(f"Event Bus Error ({name}): {e}")
            return True

        self.expose(
            _handle_frontend_event, name="__pytron_event__", run_in_thread=False
        )

        # Shell APIs
        self.expose(self.open_external, name="shell_open_external")
        self.expose(self.show_item_in_folder, name="shell_show_item_in_folder")

        # Clipboard APIs
        self.expose(self.copy_to_clipboard, name="clipboard_write_text")
        self.expose(self.get_clipboard_text, name="clipboard_read_text")

        # System Info
        self.expose(self.get_system_info, name="system_get_info")

        # Aesthetic APIs
        self.expose(self.set_window_curvature, name="window_set_curvature")
        self.expose(self.set_border_color, name="window_set_border_color")
        self.expose(self.set_background_material, name="window_set_background_material")
        self.expose(self.set_mica_effect, name="window_set_mica_effect")

        # Store APIs
        self.expose(self.store_set, name="store_set")
        self.expose(self.store_get, name="store_get")
        self.expose(self.store_delete, name="store_delete")

        # App Lifecycle
        self.expose(self.quit, name="app_quit", run_in_thread=False)
        self.expose(self.show, name="app_show", run_in_thread=False)
        self.expose(self.hide, name="app_hide", run_in_thread=False)
        self.expose(lambda: self.is_visible, name="app_is_visible", run_in_thread=False)

        # Event Bus
        self.expose(self.publish, name="app_publish")

        # Utility
        self.expose(lambda: "pong", name="app_ping")

        # Updater APIs
        self.expose(self.check_updates, name="app_check_updates")
        self.expose(self.install_update, name="app_install_update")

        # Inspector APIs (SECURITY: Only expose in debug mode)
        if self.config.get("debug", False):
            self.expose(
                self.toggle_inspector, name="app_toggle_inspector", run_in_thread=False
            )
            self.expose(
                self.open_devtools, name="app_open_devtools", run_in_thread=False
            )

    def check_updates(self, url: str):
        """
        Checks for application updates.
        Returns update info if available, else None.
        """
        from .updater import Updater

        upd = Updater(current_version=self.config.get("version"))
        return upd.check(url)

    def install_update(self, update_info: dict):
        """
        Downloads and installs an update.
        Emits 'pytron:update-progress' events.
        """
        from .updater import Updater

        upd = Updater(current_version=self.config.get("version"))

        def _on_progress(pct):
            self.broadcast("pytron:update-progress", {"percent": pct})

        # Run install in thread pool to avoid blocking IPC
        self.thread_pool.submit(upd.download_and_install, update_info, _on_progress)
        return True

    def publish(self, event_name: str, data: Any = None):
        """
        Broadcasts an event to all open windows.
        This enables simple cross-window communication.
        """
        self.broadcast(event_name, data)
        return True

    def dispatch(self, event_name: str, payload: Any = None):
        """
        Dispatches an event to the frontend Event Bus in ALL active windows.
        Uses a high-performance buffer for batching.
        """
        self._dispatch_buffer.append((event_name, payload))
        return True

    async def _flush_events_task(self):
        """Background task to flush the event buffer periodically (Low latency batching)."""
        while True:
            try:
                if self._dispatch_buffer:
                    # Collect current batch
                    batch = []
                    while self._dispatch_buffer:
                        batch.append(self._dispatch_buffer.popleft())

                    if batch:
                        # Optimization: If many events, send as a single 'pytron:batch' event
                        # If only one, send normally to keep legacy compatibility
                        if len(batch) > 1:
                            for window in self.windows:
                                if hasattr(window, "dispatch"):
                                    window.dispatch("pytron:batch", batch)
                        else:
                            name, data = batch[0]
                            for window in self.windows:
                                if hasattr(window, "dispatch"):
                                    window.dispatch(name, data)

                # Dynamic sleep: 16ms (60fps target) or 32ms (low power)
                await asyncio.sleep(0.016)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Event Flush Error: {e}")
                await asyncio.sleep(1)

    def post(self, event_name: str, payload: Any = None):
        """
        Alias for dispatch.
        Dispatches an event to the frontend Event Bus.
        Usage: app.post('user-logged-in', {'user': 'raghu'})
        """
        return self.dispatch(event_name, payload)

    def listen(self, event_name: str, func: Optional[Callable] = None):
        """
        Registers a backend listener for events coming from the frontend (pytron.emit).
        Can be used as a decorator: @app.listen('my-event')
        """
        if func is None:

            def decorator(f):
                self.listen(event_name, f)
                return f

            return decorator

        self._event_listeners[event_name].append(func)
        return func

    def unlisten(self, event_name: str, func: Optional[Callable]):
        """Removes a backend event listener."""
        if event_name in self._event_listeners:
            try:
                self._event_listeners[event_name].remove(func)
            except ValueError:
                pass

    def toggle_inspector(self):
        """
        Toggles the Pytron Inspector window.
        """
        if self.inspector:
            self.inspector.toggle()
        return True

    def open_devtools(self):
        """
        Opens developer tools for the primary window when supported.
        """
        if self.windows:
            window = self.windows[0]
            try:
                if hasattr(window, "is_alive") and not window.is_alive():
                    self.config["_pending_open_devtools"] = True
                    self.logger.info(
                        "Queued devtools open until the primary window event loop starts."
                    )
                    return True

                return bool(window.open_devtools())
            except Exception as e:
                self.logger.warning(f"Failed to open devtools: {e}")
                return False

        self.config["_pending_open_devtools"] = True
        self.logger.info("Queued devtools open until the primary window exists.")
        return True

    def load_plugins(self, plugins_dir: str):
        """Discovers and loads plugins from the specified directory."""
        return self._plugin_comp.load_plugins(plugins_dir)

    def unload_plugins(self):
        """Unloads all loaded plugins."""
        return self._plugin_comp.unload_plugins()
