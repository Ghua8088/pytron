import sys
import os
import threading
import importlib
import importlib.util

# --- SINGLE ORIGIN LOCKDOWN ---
# We store the resolved native module here to ensure
# we never load it twice from different paths.
_NATIVE_CACHE = {"module": None, "origin": None, "lock": threading.Lock()}


def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    """
    if os.path.isabs(relative_path):
        return relative_path

    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS
            full_path = os.path.join(base_path, relative_path)
            if os.path.exists(full_path):
                return full_path

        exe_path = os.path.dirname(sys.executable)
        full_path = os.path.join(exe_path, relative_path)
        if os.path.exists(full_path):
            return full_path

        try:
            base_path = os.path.dirname(__file__)
            return os.path.join(base_path, relative_path)
        except Exception:
            return os.path.join(exe_path, relative_path)
    else:
        if os.path.exists(relative_path):
            return os.path.abspath(relative_path)
        base_path = os.path.dirname(__file__)

    return os.path.join(base_path, relative_path)


def resolve_native_module():
    """
    STRICT SINGLETON RESOLVER for pytron_native.pyd.

    Rule: Exactly one NativeState may exist per process.
    Priority:
      1. Frozen _MEIPASS (highest)
      2. Frozen _internal
      3. Frozen Root
      4. Dev / Venv
      5. Fallback Package Import (lowest)

    This function discovers the module once, locks it, and returns the
    exact same module object for every subsequent call.
    """
    with _NATIVE_CACHE["lock"]:
        if _NATIVE_CACHE["module"]:
            return _NATIVE_CACHE["module"]

        # Explicit Priorities (Lower is Higher Priority)
        PRIORITY_FROZEN_MEIPASS = 10
        PRIORITY_FROZEN_INTERNAL = 20
        PRIORITY_FROZEN_ROOT = 30
        PRIORITY_DEV_LOCAL = 40
        PRIORITY_PACKAGE_FALLBACK = 99

        candidate_modules = []  # List of (priority, origin, mod)
        search_paths = []  # List of (priority, path)

        # 1. SEARCH STRATEGY
        if getattr(sys, "frozen", False):
            # FROZEN PRIORITY
            if hasattr(sys, "_MEIPASS"):
                # PyInstaller Temp Dir
                search_paths.append(
                    (
                        PRIORITY_FROZEN_MEIPASS,
                        os.path.join(sys._MEIPASS, "pytron", "dependencies"),
                    )
                )

            # Executable Dir (Nuitka / OneDir)
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            search_paths.append(
                (
                    PRIORITY_FROZEN_INTERNAL,
                    os.path.join(exe_dir, "_internal", "pytron", "dependencies"),
                )
            )

            # Also check direct executable root for flat layouts
            search_paths.append(
                (PRIORITY_FROZEN_ROOT, os.path.join(exe_dir, "dependencies"))
            )

        else:
            # DEV PRIORITY
            # Check relative to this file (pytron/utils.py -> pytron/dependencies)
            base_utils = os.path.dirname(os.path.abspath(__file__))
            search_paths.append(
                (PRIORITY_DEV_LOCAL, os.path.join(base_utils, "dependencies"))
            )

            # Site-packages fallback happens implicitly via imports below

        # Windows DLL Handling
        if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
            for _, p in search_paths:
                if os.path.exists(p):
                    try:
                        os.add_dll_directory(p)
                    except:
                        pass

        # 2. DISCOVERY

        # A) Explicit Path Discovery
        img_ext = ".pyd" if sys.platform == "win32" else ".so"
        _log_shield(f"Starting discovery (Target Ext: {img_ext})")

        for priority, path in search_paths:
            pyd_path = os.path.join(path, "pytron_native" + img_ext)
            _log_shield(f"Checking candidate: {pyd_path}")

            if os.path.exists(pyd_path):
                _log_shield(f"Found file at: {pyd_path}. Attempting load...")
                try:
                    spec = importlib.util.spec_from_file_location(
                        "pytron.dependencies.pytron_native", pyd_path
                    )
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        if hasattr(mod, "NativeState"):
                            _log_shield(
                                f"Successfully loaded NativeState from {pyd_path}"
                            )
                            candidate_modules.append((priority, pyd_path, mod))
                        else:
                            _log_shield(
                                f"Module found at {pyd_path} but missing 'NativeState' attribute."
                            )
                except Exception as e:
                    import traceback

                    err_msg = (
                        f"Load Failure for {pyd_path}: {e}\n{traceback.format_exc()}"
                    )
                    _log_shield(err_msg)
            else:
                _log_shield(f"File NOT found at: {pyd_path}")

        # B) Package Import Discovery (Fallback)
        if not candidate_modules:
            try:
                # Import without crashing
                from . import dependencies

                try:
                    native_pkg = importlib.import_module(
                        ".pytron_native", package="pytron.dependencies"
                    )
                    path = getattr(native_pkg, "__file__", "package_import")
                    candidate_modules.append(
                        (PRIORITY_PACKAGE_FALLBACK, path, native_pkg)
                    )
                except:
                    pass
            except:
                pass

        # 3. SELECTION & LOCKDOWN
        selected_mod = None
        selected_origin = None

        if candidate_modules:
            # Sort explicitly by priority (lowest number first)
            candidate_modules.sort(key=lambda x: x[0])

            # Pick FIRST (Highest Priority)
            _, selected_origin, selected_mod = candidate_modules[0]

            # Cache it
            _NATIVE_CACHE["module"] = selected_mod
            _NATIVE_CACHE["origin"] = selected_origin

            # Enforce sys.modules consistency to prevent re-importing
            sys.modules["pytron.dependencies.pytron_native"] = selected_mod
            sys.modules["pytron_native"] = selected_mod

            # Log Identity
            _log_shield(f"NativeState LOCKED to: {selected_origin}")
            return selected_mod

        # Only log "No candidates" if we didn't already log a specific "Load Failure"
        if (
            not _NATIVE_CACHE.get("last_error")
            or "Failure" not in _NATIVE_CACHE["last_error"]
        ):
            _log_shield("NativeState Resolution FAILED: No candidates found.")

        return None


def _log_shield(msg):
    # Internal logging helper
    try:
        # Save to cache for debugger access
        _NATIVE_CACHE["last_error"] = msg

        if getattr(sys, "frozen", False):
            sys.stderr.write(f"[SHIELD] {msg}\n")
            sys.stderr.flush()

        # Determine a safe log path
        if sys.platform == "win32":
            log_path = "C:/pytron_debug.log"
        else:
            log_path = "/tmp/pytron_debug.log"

        with open(log_path, "a") as f:
            f.write(f"[SHIELD] {msg}\n")
    except:
        pass


_OS_CACHE = {"module": None, "checked": False}


def resolve_os_module():
    """
    Safe resolver for pytron_os.so/.pyd.
    On Linux, we MUST skip loading this if using Native Engine to avoid GLib Schism.
    """
    if _OS_CACHE["checked"]:
        return _OS_CACHE["module"]

    res = _resolve_os_module_internal()
    _OS_CACHE["module"] = res
    _OS_CACHE["checked"] = True
    return res


def _resolve_os_module_internal():
    # 1. Linux Schism Guard (CRITICAL)
    # We MUST NOT load the OS module on Linux if using the Native Engine.
    # It initializes a competing GLib context that causes a process-wide crash.
    if sys.platform.startswith("linux"):
        # If we are running 'pytron run' or 'pytron package', we assume native context
        # unless explicitly told otherwise.
        engine = os.environ.get("PYTRON_ENGINE", "native")
        if os.environ.get("PYTRON_DEBUG_SCHISM") == "1":
            mode_desc = "Native Engine convergence" if engine == "native" else "Normal"
            print(
                f"[Pytron Debug] resolve_os_module: PROCEEDING on Linux ({mode_desc}) (Engine: {engine})."
            )

    # 2. Search for existing module
    if "pytron.dependencies.pytron_os" in sys.modules:
        return sys.modules["pytron.dependencies.pytron_os"]

    # 3. Discovery
    img_ext = ".pyd" if sys.platform == "win32" else ".so"
    search_paths = []

    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            search_paths.append(os.path.join(sys._MEIPASS, "pytron", "dependencies"))
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        search_paths.append(
            os.path.join(exe_dir, "_internal", "pytron", "dependencies")
        )
        search_paths.append(os.path.join(exe_dir, "dependencies"))
    else:
        # Dev path
        base_utils = os.path.dirname(os.path.abspath(__file__))
        search_paths.append(os.path.join(base_utils, "dependencies"))

    for path in search_paths:
        bin_path = os.path.join(path, "pytron_os" + img_ext)
        if os.path.exists(bin_path):
            try:
                # Add DLL directory for Windows dependencies
                if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(path)

                spec = importlib.util.spec_from_file_location(
                    "pytron.dependencies.pytron_os", bin_path
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    sys.modules["pytron.dependencies.pytron_os"] = mod
                    return mod
            except Exception as e:
                _log_shield(f"Failed to load pytron_os from {bin_path}: {e}")

    # Fallback to direct import if possible
    try:
        from .dependencies import pytron_os

        return pytron_os
    except:
        return None


def get_native_error_details():
    """Returns the last trapped error from native resolution if any."""
    return _NATIVE_CACHE.get("last_error", "No error captured.")


def com_thread_initializer():
    """
    Initializes COM for background threads on Windows.
    This prevents 'CoInitialize has not been called' errors when using native Windows APIs
    (like pywintypes or pywin32) inside Pytron's background thread pool.
    """
    if sys.platform == "win32":
        try:
            import ctypes

            # 2 = COINIT_APARTMENTTHREADED (STA), which is safer for UI/pywintypes compatibility.
            # 0 = COINIT_MULTITHREADED (MTA)
            ctypes.windll.ole32.CoInitializeEx(None, 2)
        except Exception:
            pass
