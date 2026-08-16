import io
import os
import sys
import types

# --- Linux Stability Guards (Nuclear Edition) ---
if sys.platform.startswith("linux"):
    # Force GSettings to memory to avoid the 'cannot register existing type GSettingsBackend' crash.
    # We use direct assignment here to OVERRIDE any system-wide settings that might cause collisions.
    os.environ["GSETTINGS_BACKEND"] = "memory"
    # PREVENT GIO from loading extra modules (like gvfs/dconf) that collision with Rust
    os.environ["GIO_EXTRA_MODULES"] = ""
    # Prevent GIO from scanning and loading backend modules (gvfs, dconf, etc.)
    # in native mode. Clearing GIO_EXTRA_MODULES is not enough because the
    # default module directory is still scanned.
    os.environ.setdefault("GIO_MODULE_DIR", "/nonexistent")
    # PREVENT accessibility bus from auto-initializing GLib
    os.environ["NO_AT_BRIDGE"] = "1"
    # PREVENT GIO from loading remote VFS modules
    os.environ["GIO_USE_VFS"] = "local"
    # Force GDK to skip OpenGL context creation to prevent EGL/DRI3/DRI2 crashes in VMs
    os.environ["GDK_DEBUG"] = "nogl"
    os.environ["GDK_GL"] = "software"
    # Force Mesa driver to bypass buggy GPU layers and use pure software CPU rasterization (llvmpipe)
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
    os.environ["GALLIUM_DRIVER"] = "llvmpipe"
    # Essential for VMs (VMware/VirtualBox) to avoid black screens or WebKit crashes.
    os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
    os.environ["WEBKIT_DISABLE_DMABUF_RENDERER"] = "1"
    # Ensure we use X11 backend for better stability in virtualized browsers.
    os.environ["WINIT_UNIX_BACKEND"] = "x11"

    # Legacy convergence hooks intentionally removed for native-mode startup.
    # In-process engines must be the single owner of GTK/WebKit symbols.
    if (
        os.environ.get("PYTRON_DEBUG_SCHISM") == "1"
        and os.environ.get("PYTRON_ENGINE", "native") == "native"
    ):
        print("[Pytron Debug] Convergence: native engine owns GTK/WebKit symbols.")

    # --- Debugging: Schism Audit ---
    if os.environ.get("PYTRON_DEBUG_SCHISM") == "1":
        print("[Pytron Debug] --- Linux Isolation Audit ---")
        for var in [
            "GSETTINGS_BACKEND",
            "GIO_EXTRA_MODULES",
            "GIO_MODULE_DIR",
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
        from importlib.metadata import PackageNotFoundError, version
    else:
        from importlib_metadata import PackageNotFoundError, version

    try:
        __version__ = version("pytron-kit")
    except PackageNotFoundError:
        __version__ = "0.0.0-dev"
except ImportError:
    __version__ = "0.0.0-dev"

# --- Plugin Configuration Namespace ---
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

from .core import App, Menu, MenuBar, Webview, get_resource_path  # noqa: E402
from .plugin import Plugin  # noqa: E402
from .testing import PytronTestClient  # noqa: E402
from .updater import Updater  # noqa: E402

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
