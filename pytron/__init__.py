import sys
import os
import io

# --- Linux Stability Guards (Nuclear Edition) ---
if sys.platform.startswith("linux"):
    # Force GSettings to memory to avoid the 'cannot register existing type GSettingsBackend' crash.
    # We use direct assignment here to OVERRIDE any system-wide settings that might cause collisions.
    os.environ["GSETTINGS_BACKEND"] = "memory"
    # PREVENT GIO from loading extra modules (like gvfs/dconf) that collision with Rust
    os.environ["GIO_EXTRA_MODULES"] = ""
    # PREVENT accessibility bus from auto-initializing GLib
    os.environ["NO_AT_BRIDGE"] = "1"
    # PREVENT GIO from loading remote VFS modules
    os.environ["GIO_USE_VFS"] = "local"
    # Essential for VMs (VMware/VirtualBox) to avoid black screens or WebKit crashes.
    os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
    # Ensure we use X11 backend for better stability in virtualized browsers.
    os.environ["WINIT_UNIX_BACKEND"] = "x11"

    # --- Global Convergence Layer ---
    # On some modern Linux distros (like Pop!_OS), loading GLib/GTK symbols in isolation
    # leads to double registration of GTypes. We force these libraries into the
    # global symbol scope to unify the registration tables between Python and Native Engine.
    import ctypes
    import ctypes.util

    # Crucial Libraries to converge
    convergence_targets = [
        "glib-2.0",
        "gobject-2.0",
        "gio-2.0",
        "gtk-3",
        "webkit2gtk-4.1",
    ]

    for lib_id in convergence_targets:
        try:
            # Dynamically resolve the best system path (e.g., /lib/x86_64-linux-gnu/libglib-2.0.so.0)
            lib_path = ctypes.util.find_library(lib_id)
            if not lib_path:
                # If find_library fails, try common sonames directly as fallback
                fallbacks = {
                    "glib-2.0": "libglib-2.0.so.0",
                    "gobject-2.0": "libgobject-2.0.so.0",
                    "gio-2.0": "libgio-2.0.so.0",
                    "gtk-3": "libgtk-3.so.0",
                    "webkit2gtk-4.1": "libwebkit2gtk-4.1.so.0",
                }
                lib_path = fallbacks.get(lib_id)

            if lib_path:
                # RTLD_GLOBAL (0x00100)
                # On some Linux distros, loading these libraries via ctypes BEFORE
                # the Rust engine causes GType registration collisions.
                # If we are using the Native Engine, we skip ctypes convergence
                # and let the Rust Engine (which is linked against these) be the source of truth.
                if os.environ.get("PYTRON_ENGINE", "native") == "native":
                    if os.environ.get("PYTRON_DEBUG_SCHISM") == "1":
                        print(
                            f"[Pytron Debug] Convergence: SKIPPING {lib_id} (Native Engine will own symbols)"
                        )
                    continue
        except:
            pass

    # --- Debugging: Schism Audit ---
    if os.environ.get("PYTRON_DEBUG_SCHISM") == "1":
        print("[Pytron Debug] --- Linux Isolation Audit ---")
        for var in [
            "GSETTINGS_BACKEND",
            "GIO_EXTRA_MODULES",
            "NO_AT_BRIDGE",
            "GIO_USE_VFS",
            "WEBKIT_DISABLE_COMPOSITING_MODE",
            "WINIT_UNIX_BACKEND",
        ]:
            print(f"[Pytron Debug] {var} = {os.environ.get(var)}")
        print("[Pytron Debug] ---------------------------")

# Best-effort: configure stdio to UTF-8 early when pytron is imported. This
# helps packaged apps avoid UnicodeEncodeError during prints/logging.
try:
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8:surrogatepass")
except Exception:
    # Environment setup is best-effort
    pass


def _early_reconfigure():
    try:
        if getattr(sys.stdout, "buffer", None) is not None:
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding="utf-8",
                errors="surrogatepass",
                line_buffering=True,
            )
    except Exception:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="surrogatepass")
        except Exception:
            # Fallback failed, cannot reconfigure stdout
            pass

    try:
        if getattr(sys.stderr, "buffer", None) is not None:
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding="utf-8",
                errors="surrogatepass",
                line_buffering=True,
            )
    except Exception:
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="surrogatepass")
        except Exception:
            # Fallback failed, cannot reconfigure stderr
            pass


# Skip reconfiguration if running under pytest to avoid conflict with capture
if "pytest" not in sys.modules and "pytest" not in sys.argv[0]:
    _early_reconfigure()

# Fetch version from installed package metadata to avoid manual updates
try:
    if sys.version_info >= (3, 8):
        from importlib.metadata import version, PackageNotFoundError
    else:
        from importlib_metadata import version, PackageNotFoundError

    try:
        __version__ = version("pytron-kit")
    except PackageNotFoundError:
        __version__ = "0.0.0-dev"
except ImportError:
    __version__ = "0.0.0-dev"

# --- Plugin Configuration Namespace ---
import types


class PluginsNamespace(types.ModuleType):
    def __init__(self):
        super().__init__("plugins")
        self._registered_configs = {}

    def __getattr__(self, name):
        # Return a configurator for the requested plugin
        return PluginConfigurator(name, self._registered_configs)

    def get_registered_config(self, plugin_name):
        return self._registered_configs.get(plugin_name, {})


class PluginConfigurator:
    def __init__(self, plugin_name, registry):
        self.plugin_name = plugin_name
        self.registry = registry

    def __call__(self, **kwargs):
        self.registry[self.plugin_name] = kwargs
        return self


# Create the instance and inject it into sys.modules so 'import plugins' works
plugins = PluginsNamespace()
sys.modules["plugins"] = plugins
# print(f"[Pytron] Injected plugins namespace into sys.modules: {sys.modules['plugins']}")
# --------------------------------------

from .core import App, Webview, get_resource_path, Menu, MenuBar
from .plugin import Plugin
from .updater import Updater
from .testing import PytronTestClient

__all__ = [
    "App",
    "Webview",
    "get_resource_path",
    "Menu",
    "MenuBar",
    "Plugin",
    "Updater",
    "plugins",
    "PluginConfigurator",
    "PytronTestClient",
]
