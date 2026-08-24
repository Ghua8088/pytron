import ctypes
import os
import sys

from ...utils import resolve_native_bridge
from . import toasts
from .constants import (
    BIF_NEWDIALOGSTYLE,
    BIF_RETURNONLYFSDIRS,
    BROWSEINFOW,
    NIF_ICON,
    NIF_INFO,
    NIF_TIP,
    NIIF_INFO,
    NIM_ADD,
    NIM_MODIFY,
    NIM_SETVERSION,
    NOTIFYICON_VERSION_4,
    NOTIFYICONDATAW,
    OFN_EXPLORER,
    OFN_FILEMUSTEXIST,
    OFN_NOCHANGEDIR,
    OFN_OVERWRITEPROMPT,
    OFN_PATHMUSTEXIST,
    OPENFILENAMEW,
)
from .utils import get_hwnd

_AUTO_NATIVE_BRIDGE = object()
pytron_native = _AUTO_NATIVE_BRIDGE


def _get_native_bridge():
    if pytron_native is _AUTO_NATIVE_BRIDGE:
        return resolve_native_bridge()
    return pytron_native


try:
    import winreg
except ImportError:
    winreg = None

try:
    import ctypes.wintypes
except ImportError:
    # Safe fallback for non-Windows imports
    class MockWintypes:
        HWND = ctypes.c_void_p
        BOOL = ctypes.c_int
        WPARAM = ctypes.c_void_p
        LPARAM = ctypes.c_void_p
        RECT = ctypes.c_void_p

    ctypes.wintypes = MockWintypes

# -------------------------------------------------------------------
# Hardened Library Wrappers
# -------------------------------------------------------------------
try:
    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32
    kernel32 = ctypes.windll.kernel32
    comdlg32 = ctypes.windll.comdlg32
except AttributeError:
    # Non-Windows Platform
    user32 = None
    shell32 = None
    kernel32 = None
    comdlg32 = None


if user32 and shell32 and kernel32 and comdlg32:
    # --- USER32 ---
    user32.LoadImageW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.LoadImageW.restype = ctypes.c_void_p  # HANDLE

    user32.LoadIconW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]  # Used with ID
    user32.LoadIconW.restype = ctypes.c_void_p

    user32.MessageBoxW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint,
    ]
    user32.MessageBoxW.restype = ctypes.c_int

    user32.SendMessageW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    ]
    user32.SendMessageW.restype = ctypes.c_longlong  # LRESULT can be 64-bit

    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.wintypes.BOOL

    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.wintypes.BOOL

    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p

    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.wintypes.BOOL

    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p

    # --- SHELL32 ---
    shell32.Shell_NotifyIconW.argtypes = [
        ctypes.c_ulong,
        ctypes.POINTER(NOTIFYICONDATAW),
    ]
    shell32.Shell_NotifyIconW.restype = ctypes.wintypes.BOOL

    shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
    shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long  # HRESULT

    shell32.SHBrowseForFolderW.argtypes = [ctypes.POINTER(BROWSEINFOW)]
    shell32.SHBrowseForFolderW.restype = ctypes.c_void_p  # PIDLIST_ABSOLUTE

    shell32.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    shell32.SHGetPathFromIDListW.restype = ctypes.wintypes.BOOL

    shell32.ILFree.argtypes = [ctypes.c_void_p]
    shell32.ILFree.restype = None

    # --- KERNEL32 ---
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p

    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p

    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.wintypes.BOOL

    # --- COMDLG32 ---
    comdlg32.GetOpenFileNameW.argtypes = [ctypes.POINTER(OPENFILENAMEW)]
    comdlg32.GetOpenFileNameW.restype = ctypes.wintypes.BOOL

    comdlg32.GetSaveFileNameW.argtypes = [ctypes.POINTER(OPENFILENAMEW)]
    comdlg32.GetSaveFileNameW.restype = ctypes.wintypes.BOOL

# -------------------------------------------------------------------
# Operations
# -------------------------------------------------------------------


def notification(w, title, message, icon=None):
    native_bridge = _get_native_bridge()
    if native_bridge:
        try:
            hwnd = get_hwnd(w)
            if hwnd:
                native_bridge.show_notification(
                    hwnd, title, message, str(os.path.abspath(icon)) if icon else None
                )
                return
        except Exception as e:
            print(f"[Pytron] Notification error (pytron_native): {e}")

    try:
        hwnd = get_hwnd(w)
        # Even if hwnd is None (e.g. hidden mode), we might need a dummy HWND for the tray api.
        # However, linking it to the main webview HWND is standard.
        if not hwnd:
            print(f"[Pytron] Notification skipped: No valid HWND for window {w}")
            return

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = hwnd
        nid.uID = 2000  # Unique ID for "Toast" source

        # 1. Ensure Icon is Valid
        h_icon = 0
        if icon and os.path.exists(icon):
            h_icon = user32.LoadImageW(None, str(icon), 1, 16, 16, 0x00000010)
        if not h_icon:
            h_icon = user32.LoadIconW(None, ctypes.c_void_p(32512))  # IDI_APPLICATION

        nid.hIcon = h_icon

        # 2. Strict ctypes definition (Local Override similar to tray.py)
        shell32.Shell_NotifyIconW.argtypes = [
            ctypes.c_ulong,
            ctypes.POINTER(NOTIFYICONDATAW),
        ]
        shell32.Shell_NotifyIconW.restype = ctypes.wintypes.BOOL

        # 3. ADD the Icon first (if not exists)
        # We need NIF_ICON so it exists. We assume it might already exist.
        nid.uFlags = NIF_ICON | NIF_TIP
        nid.szTip = title[:127] if title else "Notification"

        # Try ADD. If it fails, it might already exist, so we treat it as success-ish
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

        # 4. Set Version to 4 (Vista+) to enable modern "Balloon/Toast" behavior
        nid.uVersion = NOTIFYICON_VERSION_4
        shell32.Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(nid))

        # 5. Show The Toast (MODIFY)
        nid.uFlags = NIF_INFO | NIF_ICON | NIF_TIP
        nid.szInfo = message[:255]
        nid.szInfoTitle = title[:63]
        nid.dwInfoFlags = NIIF_INFO  # | NIIF_LARGE_ICON if we had a large icon

        success = shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))

        if not success:
            err = ctypes.get_last_error()
            print(f"[Pytron] Notification Failed. Error Code: {err}")

    except Exception as e:
        print(f"[Pytron] Notification Exception: {e}")


def toast(w, config):
    try:
        # Pass the window handle if info is needed, but toasts are mostly process-wide
        toasts.show_toast(w, config)
    except Exception as e:
        print(f"[Pytron] Rich Toast Exception: {e}")


def message_box(w, title, message, style=0):
    if pytron_native:
        try:
            return pytron_native.message_box(get_hwnd(w), title, message, style)
        except Exception:
            pass
    hwnd = get_hwnd(w)
    return user32.MessageBoxW(hwnd, message, title, style)


def _ensure_ico_file(icon_path):
    if not icon_path or not os.path.exists(icon_path):
        return icon_path
    if icon_path.lower().endswith(".ico"):
        return icon_path

    ico_candidate = os.path.splitext(icon_path)[0] + ".ico"
    if os.path.exists(ico_candidate):
        return ico_candidate

    try:
        from PIL import Image

        img = Image.open(icon_path)
        ico_dir = os.path.join(os.path.expanduser("~"), ".pytron", "cache", "icons")
        os.makedirs(ico_dir, exist_ok=True)
        import hashlib

        h = hashlib.md5(os.path.abspath(icon_path).encode("utf-8")).hexdigest()
        cache_ico = os.path.join(ico_dir, f"icon_{h}.ico")

        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(cache_ico, format="ICO", sizes=sizes)
        return cache_ico
    except Exception:
        pass

    return icon_path


def _load_hicon_gdiplus(icon_path):
    try:
        gdiplus = ctypes.windll.gdiplus

        class GdiplusStartupInput(ctypes.Structure):
            _fields_ = [
                ("GdiplusVersion", ctypes.c_uint32),
                ("DebugEventCallback", ctypes.c_void_p),
                ("SuppressBackgroundThread", ctypes.c_int32),
                ("SuppressExternalCodecs", ctypes.c_int32),
            ]

        input_struct = GdiplusStartupInput(1, None, 0, 0)
        token = ctypes.c_ulonglong()
        if (
            gdiplus.GdiplusStartup(
                ctypes.byref(token), ctypes.byref(input_struct), None
            )
            != 0
        ):
            return None
        p_bitmap = ctypes.c_void_p()
        if (
            gdiplus.GdipCreateBitmapFromFile(
                ctypes.c_wchar_p(str(os.path.abspath(icon_path))),
                ctypes.byref(p_bitmap),
            )
            != 0
        ):
            gdiplus.GdiplusShutdown(token)
            return None
        h_icon = ctypes.c_void_p()
        if gdiplus.GdipCreateHICONFromBitmap(p_bitmap, ctypes.byref(h_icon)) != 0:
            gdiplus.GdipDisposeImage(p_bitmap)
            gdiplus.GdiplusShutdown(token)
            return None
        gdiplus.GdipDisposeImage(p_bitmap)
        return h_icon
    except Exception:
        return None


def set_window_icon(w, icon_path):
    if not icon_path or not os.path.exists(icon_path):
        return

    icon_path = _ensure_ico_file(icon_path)

    if pytron_native:
        try:
            pytron_native.set_window_icon(get_hwnd(w), str(os.path.abspath(icon_path)))
            return
        except Exception:
            pass
    hwnd = get_hwnd(w)
    try:
        # LR_LOADFROMFILE | LR_DEFAULTSIZE
        flags = 0x00000010 | 0x00000040

        h_small = user32.LoadImageW(None, str(icon_path), 1, 16, 16, flags)
        if h_small:
            user32.SendMessageW(hwnd, 0x0080, 0, h_small)  # WM_SETICON, ICON_SMALL

        h_big = user32.LoadImageW(None, str(icon_path), 1, 32, 32, flags)
        if h_big:
            user32.SendMessageW(hwnd, 0x0080, 1, h_big)  # WM_SETICON, ICON_BIG

        if not h_small and not h_big:
            # Fallback for PNG/JPG image formats using GDI+
            h_gdi = _load_hicon_gdiplus(icon_path)
            if h_gdi:
                user32.SendMessageW(hwnd, 0x0080, 0, h_gdi)  # WM_SETICON, ICON_SMALL
                user32.SendMessageW(hwnd, 0x0080, 1, h_gdi)  # WM_SETICON, ICON_BIG
    except Exception as e:
        print(f"Icon error: {e}")


def _prepare_ofn(w, title, default_path, file_types, file_buffer_size=1024):
    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.hwndOwner = get_hwnd(w)

    buff = ctypes.create_unicode_buffer(file_buffer_size)
    ofn.lpstrFile = ctypes.addressof(buff)
    ofn.nMaxFile = file_buffer_size

    if title:
        ofn.lpstrTitle = title

    if default_path:
        if os.path.isfile(default_path):
            d = os.path.dirname(default_path)
            n = os.path.basename(default_path)
            ofn.lpstrInitialDir = d
            buff.value = n
        else:
            ofn.lpstrInitialDir = default_path

    if not file_types:
        file_types = "All Files (*.*)|*.*"

    if isinstance(file_types, (list, tuple)):
        # Convert list of tuples [("Name", "*.ext"), ...] to "Name|*.ext|..."
        # Or if it's a list of strings ["Name|*.ext", ...], just join them.
        ft_parts = []
        for ft in file_types:
            if isinstance(ft, (list, tuple)) and len(ft) >= 2:
                # Ensure the description doesn't contain pipes, though patterns might
                ft_parts.append(f"{ft[0]}|{ft[1]}")
            else:
                ft_parts.append(str(ft))
        file_types = "|".join(ft_parts)

    filter_str = file_types.replace("|", "\0") + "\0"
    ofn.lpstrFilter = filter_str

    return ofn, buff


def open_file_dialog(w, title, default_path=None, file_types=None):
    native_bridge = _get_native_bridge()
    if native_bridge:
        hwnd = get_hwnd(w)
        try:
            # Attempt the parented dialog first. rfd returns None for two reasons:
            #   (a) the user cancelled  — we must NOT retry, just return None.
            #   (b) the dialog never opened (parenting failure, very rare).
            # We cannot tell (a) from (b) on a None return, so we treat None as
            # a clean cancel and return immediately. Only a raised *exception*
            # indicates a real failure that warrants a parentless retry.
            return native_bridge.open_file_dialog(hwnd, title, default_path, file_types)
        except Exception as e:
            # A real error occurred (e.g. invalid HWND, rfd panic). Retry once
            # without a parent window so the dialog can still open.
            if hwnd != 0:
                print(f"[Pytron] open_file_dialog: parented call failed ({e}), retrying parentless.")
                try:
                    return native_bridge.open_file_dialog(0, title, default_path, file_types)
                except Exception as ex:
                    print(f"[Pytron] open_file_dialog: parentless fallback also failed: {ex}")

    # Final fallback: Win32 GetOpenFileNameW (no native bridge available)
    ofn, buff = _prepare_ofn(w, title, default_path, file_types)
    ofn.Flags = OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR
    if comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
        return buff.value
    return None


def save_file_dialog(w, title, default_path=None, default_name=None, file_types=None):
    native_bridge = _get_native_bridge()
    if native_bridge:
        hwnd = get_hwnd(w)
        try:
            # Same logic as open_file_dialog: None == user cancelled, don't retry.
            # Only retry on a raised exception (a real native error).
            return native_bridge.save_file_dialog(hwnd, title, default_path, default_name, file_types)
        except Exception as e:
            if hwnd != 0:
                print(f"[Pytron] save_file_dialog: parented call failed ({e}), retrying parentless.")
                try:
                    return native_bridge.save_file_dialog(0, title, default_path, default_name, file_types)
                except Exception as ex:
                    print(f"[Pytron] save_file_dialog: parentless fallback also failed: {ex}")

    # Final fallback: Win32 GetSaveFileNameW
    path = default_path
    if default_name:
        path = os.path.join(path, default_name) if path else default_name

    ofn, buff = _prepare_ofn(w, title, path, file_types)
    ofn.Flags = OFN_EXPLORER | OFN_OVERWRITEPROMPT | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR

    if comdlg32.GetSaveFileNameW(ctypes.byref(ofn)):
        return buff.value
    return None


def open_folder_dialog(w, title, default_path=None):
    native_bridge = _get_native_bridge()
    if native_bridge:
        hwnd = get_hwnd(w)
        try:
            # None == user cancelled. Only retry on a raised exception.
            return native_bridge.open_folder_dialog(hwnd, title, default_path)
        except Exception as e:
            if hwnd != 0:
                print(f"[Pytron] open_folder_dialog: parented call failed ({e}), retrying parentless.")
                try:
                    return native_bridge.open_folder_dialog(0, title, default_path)
                except Exception as ex:
                    print(f"[Pytron] open_folder_dialog: parentless fallback also failed: {ex}")

    # Final fallback: Win32 SHBrowseForFolderW
    bif = BROWSEINFOW()
    bif.hwndOwner = get_hwnd(w)
    bif.lpszTitle = title
    bif.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE

    pidl = shell32.SHBrowseForFolderW(ctypes.byref(bif))
    if pidl:
        path = ctypes.create_unicode_buffer(260)
        if shell32.SHGetPathFromIDListW(pidl, path):
            shell32.ILFree(pidl)
            return path.value
        shell32.ILFree(pidl)
    return None


def register_protocol(scheme):
    if not winreg:
        return False
    try:
        exe = sys.executable
        if getattr(sys, "frozen", False):
            command = f'"{exe}" "%1"'
        else:
            main_file = os.path.abspath(sys.modules["__main__"].__file__)
            command = f'"{exe}" "{main_file}" "%1"'

        key_path = f"Software\\Classes\\{scheme}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"URL:{scheme} Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, f"{key_path}\\shell\\open\\command"
        ) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
        return True
    except Exception:
        return False


def set_launch_on_boot(app_name, exe_path, enable=True):
    native_bridge = _get_native_bridge()
    if native_bridge:
        try:
            result = native_bridge.set_launch_on_boot(app_name, exe_path, enable)
            if result:
                return result
        except Exception:
            pass

    if pytron_native is _AUTO_NATIVE_BRIDGE:
        try:
            import pytron.dependencies as _deps

            legacy_bridge = getattr(_deps, "pytron_native", None)
            if legacy_bridge:
                result = legacy_bridge.set_launch_on_boot(app_name, exe_path, enable)
                if result:
                    return result
        except Exception:
            pass

    if not winreg:
        return False
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
        ) as key:
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False


def set_app_id(app_id):
    native_bridge = _get_native_bridge()
    if native_bridge:
        try:
            native_bridge.set_app_id(app_id)
            return
        except Exception:
            pass
    try:
        shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as e:
        print(f"[Pytron] Debug: Failed to set app model ID: {e}")


def set_taskbar_progress(w, state="normal", value=0, max_value=100):
    native_bridge = _get_native_bridge()
    if native_bridge:
        try:
            hwnd = get_hwnd(w)
            native_bridge.set_taskbar_progress(hwnd, state, int(value), int(max_value))
            return
        except Exception as e:
            print(f"[Pytron] Taskbar progress error (pytron_native): {e}")


def set_clipboard_text(text: str):
    """Copies text to the system clipboard."""
    native_bridge = _get_native_bridge()
    if native_bridge:
        try:
            res = native_bridge.set_clipboard_text(text)
            if res is not None:
                return bool(res)
        except Exception as e:
            print(f"[Pytron] Clipboard Set Error (pytron_native): {e}")

    if not (user32 and kernel32):
        return False

    try:
        if not user32.OpenClipboard(None):
            return False

        try:
            user32.EmptyClipboard()

            text_buffer = ctypes.create_unicode_buffer(text)
            size = ctypes.sizeof(text_buffer)
            h_mem = kernel32.GlobalAlloc(0x0002, size)  # GMEM_MOVEABLE
            if not h_mem:
                return False

            p_mem = kernel32.GlobalLock(h_mem)
            if not p_mem:
                return False

            ctypes.memmove(p_mem, ctypes.addressof(text_buffer), size)
            kernel32.GlobalUnlock(h_mem)

            return bool(user32.SetClipboardData(13, h_mem))  # CF_UNICODETEXT
        finally:
            user32.CloseClipboard()
    except Exception as e:
        print(f"[Pytron] Clipboard Set Error (ctypes): {e}")
        return False


def get_clipboard_text():
    """Returns text from the system clipboard."""
    native_bridge = _get_native_bridge()
    if native_bridge:
        try:
            res = native_bridge.get_clipboard_text()
            if res is not None:
                return res
        except Exception as e:
            print(f"[Pytron] Clipboard Get Error (pytron_native): {e}")

    if not user32:
        return None

    try:
        if not user32.OpenClipboard(None):
            return None

        try:
            handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
            if not handle:
                return None

            return ctypes.wstring_at(handle)
        finally:
            user32.CloseClipboard()
    except Exception as e:
        print(f"[Pytron] Clipboard Get Error (ctypes): {e}")
        return None


def get_system_info():
    """Returns platform core information."""
    import os
    import sys

    # Avoid platform.system() as it may hang on some Windows environments
    info = {
        "os": sys.platform,
        "arch": os.environ.get("PROCESSOR_ARCHITECTURE", "unknown"),
        "release": (
            sys.getwindowsversion().major if sys.platform == "win32" else "unknown"
        ),
        "version": sys.version,
        "cpu_count": os.cpu_count(),
    }

    try:
        import psutil

        mem = psutil.virtual_memory()
        info["ram_total"] = mem.total
        info["ram_available"] = mem.available
        info["cpu_usage"] = psutil.cpu_percent(interval=None)
    except ImportError:
        pass

    return info


def enable_drag_drop_safe(w, callback):
    # Legacy Native Hook - Disabled in favor of JS Bridge
    pass
