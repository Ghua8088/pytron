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

        # Safeguard: Check if pytron_native was already imported and registered in sys.modules
        for name in ["pytron.dependencies.pytron_native", "pytron_native"]:
            if name in sys.modules and sys.modules[name]:
                mod = sys.modules[name]
                if hasattr(mod, "NativeState"):
                    _NATIVE_CACHE["module"] = mod
                    _NATIVE_CACHE["origin"] = getattr(mod, "__file__", "sys.modules")
                    _log_shield(
                        f"NativeState recovered from sys.modules: {_NATIVE_CACHE['origin']}"
                    )
                    return mod

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

            # 1. Check standard 'pytron/dependencies' at root (OneDir)
            search_paths.append(
                (
                    PRIORITY_FROZEN_ROOT,
                    os.path.join(exe_dir, "pytron", "dependencies"),
                )
            )

            # 2. Check within _internal for modern PyInstaller structure
            search_paths.append(
                (
                    PRIORITY_FROZEN_INTERNAL,
                    os.path.join(exe_dir, "_internal", "pytron", "dependencies"),
                )
            )

            # 3. Legacy Flat Root Check (Fallback)
            search_paths.append(
                (PRIORITY_FROZEN_ROOT + 5, os.path.join(exe_dir, "dependencies"))
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

        candidates = []
        for priority, path in search_paths:
            pyd_path = os.path.join(path, "pytron_native" + img_ext)
            _log_shield(f"Checking candidate: {pyd_path}")

            if os.path.exists(pyd_path):
                norm_path = os.path.normpath(pyd_path)
                # Avoid checking the same physical file twice
                if norm_path not in [c[1] for c in candidates]:
                    candidates.append((priority, norm_path))
                    _log_shield(f"Found candidate: {norm_path} (priority={priority})")
            else:
                _log_shield(f"File NOT found at: {pyd_path}")

        # Sort candidates by priority (lowest number first)
        candidates.sort(key=lambda x: x[0])

        for priority, pyd_path in candidates:
            _log_shield(f"Attempting load: {pyd_path}...")
            try:
                spec = importlib.util.spec_from_file_location(
                    "pytron.dependencies.pytron_native", pyd_path
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "NativeState"):
                        _log_shield(f"Successfully loaded NativeState from {pyd_path}")
                        candidate_modules.append((priority, pyd_path, mod))
                        # Break immediately on first successful load to prevent PyO3 double-load crash
                        break
                    else:
                        _log_shield(
                            f"Module found at {pyd_path} but missing 'NativeState' attribute."
                        )
            except Exception as e:
                import traceback

                err_msg = f"Load Failure for {pyd_path}: {e}\n{traceback.format_exc()}"
                _log_shield(err_msg)

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


def resolve_native_bridge():
    """
    Resolve the shared native bridge used for platform hooks.
    """
    return resolve_native_module()


def _log_shield(msg):
    # Internal logging helper
    try:
        # Save to cache for debugger access
        _NATIVE_CACHE["last_error"] = msg

        if getattr(sys, "frozen", False):
            try:
                if sys.stderr and not getattr(sys.stderr, "closed", False):
                    sys.stderr.write(f"[SHIELD] {msg}\n")
                    sys.stderr.flush()
            except Exception:
                pass

        # Determine a safe log path
        if sys.platform == "win32":
            log_path = "C:/pytron_debug.log"
        else:
            log_path = "/tmp/pytron_debug.log"

        try:
            with open(log_path, "a") as f:
                f.write(f"[SHIELD] {msg}\n")
        except Exception:
            pass
    except Exception:
        pass


_OS_CACHE = {"module": None, "checked": False}


def resolve_os_module():
    """
    Deprecated compatibility resolver.
    pytron_os has been retired in favor of pytron_native.
    """
    _OS_CACHE["checked"] = True
    _OS_CACHE["module"] = None
    return None


def _resolve_os_module_internal():
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
