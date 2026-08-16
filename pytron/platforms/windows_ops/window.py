import ctypes

try:
    import ctypes.wintypes
except ImportError:
    ctypes.wintypes = None
from ...utils import resolve_native_bridge
from .constants import (
    DWMWA_BORDER_COLOR,
    DWMWA_WINDOW_CORNER_PREFERENCE,
    DWMWCP_ROUND,
    GWL_EXSTYLE,
    GWL_STYLE,
    HTCAPTION,
    SW_HIDE,
    SW_SHOW,
    SWP_FRAMECHANGED,
    SWP_NOACTIVATE,
    SWP_NOMOVE,
    SWP_NOSIZE,
    SWP_NOZORDER,
    WM_CLOSE,
    WM_NCLBUTTONDOWN,
    WS_CAPTION,
    WS_EX_APPWINDOW,
    WS_EX_TOOLWINDOW,
    WS_THICKFRAME,
)
from .utils import get_hwnd


class _NativeBridgeProxy:
    def __bool__(self):
        return resolve_native_bridge() is not None

    def __getattr__(self, name):
        bridge = resolve_native_bridge()
        if bridge is None:
            raise AttributeError(name)
        return getattr(bridge, name)


pytron_native = _NativeBridgeProxy()

try:
    user32 = ctypes.windll.user32
except AttributeError:
    user32 = None


if user32:
    # Function Prototyping (Safe)

    # ShowWindow
    user32.ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = ctypes.wintypes.BOOL

    # SetWindowPos
    user32.SetWindowPos.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = ctypes.wintypes.BOOL

    # PostMessageW
    user32.PostMessageW.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.c_uint,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    ]
    user32.PostMessageW.restype = ctypes.wintypes.BOOL

    # IsZoomed
    user32.IsZoomed.argtypes = [ctypes.wintypes.HWND]
    user32.IsZoomed.restype = ctypes.wintypes.BOOL

    # GetWindowLongW
    user32.GetWindowLongW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long

    # SetWindowLongW
    user32.SetWindowLongW.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.c_int,
        ctypes.c_long,
    ]
    user32.SetWindowLongW.restype = ctypes.c_long

    # ReleaseCapture
    user32.ReleaseCapture.argtypes = []
    user32.ReleaseCapture.restype = ctypes.wintypes.BOOL

    # SendMessageW
    user32.SendMessageW.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.c_uint,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    ]
    user32.SendMessageW.restype = ctypes.wintypes.LPARAM

    # IsWindowVisible
    user32.IsWindowVisible.argtypes = [ctypes.wintypes.HWND]
    user32.IsWindowVisible.restype = ctypes.wintypes.BOOL

    # SetForegroundWindow
    user32.SetForegroundWindow.argtypes = [ctypes.wintypes.HWND]
    user32.SetForegroundWindow.restype = ctypes.wintypes.BOOL

    # GetWindowRect
    user32.GetWindowRect.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.POINTER(ctypes.wintypes.RECT),
    ]
    user32.GetWindowRect.restype = ctypes.wintypes.BOOL

    # GetSystemMetrics
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int

    # SetWindowTextW
    user32.SetWindowTextW.argtypes = [ctypes.wintypes.HWND, ctypes.c_wchar_p]
    user32.SetWindowTextW.restype = ctypes.wintypes.BOOL

    # GetWindowLongPtrW - Check if available
    if hasattr(user32, "GetWindowLongPtrW"):
        user32.GetWindowLongPtrW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            user32.GetWindowLongPtrW.restype = ctypes.c_longlong
        else:
            user32.GetWindowLongPtrW.restype = ctypes.c_long

    # SetWindowLongPtrW - Check if available
    if hasattr(user32, "SetWindowLongPtrW"):
        user32.SetWindowLongPtrW.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.c_int,
            ctypes.c_void_p,
        ]
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            user32.SetWindowLongPtrW.restype = ctypes.c_longlong
        else:
            user32.SetWindowLongPtrW.restype = ctypes.c_long

    # CallWindowProcW
    user32.CallWindowProcW.argtypes = [
        ctypes.c_void_p,
        ctypes.wintypes.HWND,
        ctypes.c_uint,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    ]
    user32.CallWindowProcW.restype = ctypes.wintypes.LPARAM

    # DrawMenuBar
    user32.DrawMenuBar.argtypes = [ctypes.wintypes.HWND]
    user32.DrawMenuBar.restype = ctypes.wintypes.BOOL

    # MonitorFromWindow
    user32.MonitorFromWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_uint]
    user32.MonitorFromWindow.restype = ctypes.c_void_p

    # GetMonitorInfoW
    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_uint),
            ("rcMonitor", ctypes.wintypes.RECT),
            ("rcWork", ctypes.wintypes.RECT),
            ("dwFlags", ctypes.c_uint),
        ]

    user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
    user32.GetMonitorInfoW.restype = ctypes.wintypes.BOOL


_fullscreen_storage = {}


def set_fullscreen(w, enable):
    if pytron_native:
        try:
            return pytron_native.set_fullscreen(get_hwnd(w), enable)
        except Exception:
            pass

    hwnd = get_hwnd(w)
    if not hwnd:
        return

    if enable:
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        _fullscreen_storage[hwnd] = {
            "style": user32.GetWindowLongW(hwnd, GWL_STYLE),
            "rect": (rect.left, rect.top, rect.right, rect.bottom),
        }
        new_style = _fullscreen_storage[hwnd]["style"] & ~WS_CAPTION & ~WS_THICKFRAME
        user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)

        hmon = user32.MonitorFromWindow(hwnd, 2)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        r = mi.rcMonitor
        user32.SetWindowPos(
            hwnd,
            -1,
            r.left,
            r.top,
            r.right - r.left,
            r.bottom - r.top,
            SWP_FRAMECHANGED,
        )
    else:
        if hwnd in _fullscreen_storage:
            data = _fullscreen_storage.pop(hwnd)
            user32.SetWindowLongW(hwnd, GWL_STYLE, data["style"])
            left, top, right, bottom = data["rect"]
            user32.SetWindowPos(
                hwnd, 0, left, top, right - left, bottom - top, SWP_FRAMECHANGED
            )


def minimize(w):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    if pytron_native:
        try:
            return pytron_native.minimize(hwnd)
        except Exception:
            pass
    # No fallback — Native Bridge Mandatory


def maximize(w):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    if pytron_native:
        try:
            return pytron_native.maximize(hwnd)
        except Exception:
            pass
    # No fallback — Native Bridge Mandatory


def restore(w):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    if pytron_native:
        try:
            return pytron_native.restore(hwnd)
        except Exception:
            pass
    # No fallback — Native Bridge Mandatory


def set_title(w, title):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    if pytron_native:
        try:
            return pytron_native.set_title(hwnd, title)
        except Exception:
            pass
    # No fallback — Native Bridge Mandatory


def set_bounds(w, x, y, width, height, no_move=False):
    hwnd = get_hwnd(w)
    if not hwnd:
        return

    if pytron_native:
        try:
            return pytron_native.set_bounds(
                hwnd, int(x), int(y), int(width), int(height), no_move, False
            )
        except Exception:
            pass

    flags = SWP_NOZORDER | SWP_NOACTIVATE
    if no_move or (x == -1 and y == -1):
        flags |= SWP_NOMOVE
    user32.SetWindowPos(hwnd, 0, int(x), int(y), int(width), int(height), flags)


def close(w):
    if pytron_native:
        try:
            return pytron_native.close(get_hwnd(w))
        except Exception:
            pass
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def toggle_maximize(w):
    hwnd = get_hwnd(w)
    if not hwnd:
        return False
    if pytron_native:
        try:
            return pytron_native.toggle_maximize(hwnd)
        except Exception:
            pass
    if user32.IsZoomed(hwnd):
        restore(hwnd)
        return False
    else:
        maximize(hwnd)
        return True


def set_always_on_top(w, enable):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    if pytron_native:
        try:
            return pytron_native.set_always_on_top(hwnd, enable)
        except Exception:
            pass
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    hwnd_insert_after = HWND_TOPMOST if enable else HWND_NOTOPMOST
    user32.SetWindowPos(
        hwnd, hwnd_insert_after, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    )


def make_frameless(w):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    if pytron_native:
        try:
            return pytron_native.make_frameless(hwnd)
        except Exception:
            pass
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    style = style & ~WS_CAPTION
    user32.SetWindowLongW(hwnd, GWL_STYLE, style)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0020 | 0x0001 | 0x0002 | 0x0004 | 0x0010)


def set_utility_window(w, enable):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    if pytron_native:
        try:
            return pytron_native.set_utility_window(hwnd, enable)
        except Exception:
            pass
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if enable:
        ex_style = (ex_style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
    else:
        ex_style = (ex_style | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
    user32.SetWindowPos(
        hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
    )


def start_drag(w):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    if pytron_native:
        try:
            return pytron_native.start_drag(hwnd)
        except Exception:
            pass
    user32.ReleaseCapture()
    user32.SendMessageW(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)


def hide(w):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    if pytron_native:
        try:
            return pytron_native.hide(hwnd)
        except Exception:
            pass
    user32.ShowWindow(hwnd, SW_HIDE)


def is_visible(w):
    hwnd = get_hwnd(w)
    if not hwnd:
        return False
    if pytron_native:
        try:
            return pytron_native.is_visible(hwnd)
        except Exception:
            pass
    return bool(user32.IsWindowVisible(hwnd))


def show(w):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    if pytron_native:
        try:
            return pytron_native.show(hwnd)
        except Exception:
            pass
    user32.ShowWindow(hwnd, SW_SHOW)
    user32.SetForegroundWindow(hwnd)


def center(w, width=None, height=None):
    hwnd = get_hwnd(w)
    if not hwnd:
        return

    # Use Python-native implementation for centering (more stable for multi-monitor)
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))

    current_width = rect.right - rect.left
    current_height = rect.bottom - rect.top

    if width is None:
        width = current_width
    if height is None:
        height = current_height

    # Fallback for hidden windows with 0x0 size at startup
    if width <= 0 or height <= 0:
        width, height = 800, 600

    # Multi-monitor aware centering
    # MONITOR_DEFAULTTONEAREST = 2
    hmon = user32.MonitorFromWindow(hwnd, 2)

    # Re-use MONITORINFO from constants or local structure
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
        # rcWork excludes taskbar
        r = mi.rcWork
        screen_width = r.right - r.left
        screen_height = r.bottom - r.top
        x = r.left + (screen_width - width) // 2
        y = r.top + (screen_height - height) // 2
    else:
        # Fallback to primary monitor
        screen_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        screen_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

    # SWP_NOZORDER (0x0004) | SWP_NOACTIVATE (0x0010)
    # We remove SWP_NOSIZE if we actually want to resize the window during centering
    flags = 0x0014  # SWP_NOZORDER | SWP_NOACTIVATE
    user32.SetWindowPos(hwnd, 0, x, y, int(width), int(height), flags)


_wnd_procs = {}


def set_menu(w, menu_bar):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    menu_bar.build_for_windows(hwnd)
    WNDPROC = ctypes.WINFUNCTYPE(
        ctypes.c_longlong,
        ctypes.wintypes.HWND,
        ctypes.wintypes.UINT,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    )
    from .constants import GWL_WNDPROC, WM_COMMAND

    old_proc = user32.GetWindowLongPtrW(hwnd, GWL_WNDPROC)

    def new_wnd_proc(hwnd_in, msg, wparam, lparam):
        if msg == WM_COMMAND:
            cmd_id = wparam & 0xFFFF
            if menu_bar.handle_command(cmd_id):
                return 0
        return user32.CallWindowProcW(old_proc, hwnd_in, msg, wparam, lparam)

    new_proc_inst = WNDPROC(new_wnd_proc)
    _wnd_procs[hwnd] = (new_proc_inst, old_proc)
    new_proc_ptr = (
        ctypes.c_void_p(new_proc_inst) if hasattr(ctypes, "c_void_p") else new_proc_inst
    )
    user32.SetWindowLongPtrW(hwnd, GWL_WNDPROC, new_proc_ptr)
    user32.DrawMenuBar(hwnd)


def set_border_color(w, color_hex):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    if pytron_native:
        try:
            color_hex = color_hex.lstrip("#")
            if len(color_hex) == 6:
                r = int(color_hex[0:2], 16)
                g = int(color_hex[2:4], 16)
                b = int(color_hex[4:6], 16)
                color_ref = b << 16 | g << 8 | r
            elif len(color_hex) == 8:
                r = int(color_hex[2:4], 16)
                g = int(color_hex[4:6], 16)
                b = int(color_hex[6:8], 16)
                color_ref = b << 16 | g << 8 | r
            else:
                return
            pytron_native.set_border_color(hwnd, color_ref)
            return
        except Exception:
            pass
    try:
        dwmapi = ctypes.windll.dwmapi
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_BORDER_COLOR, ctypes.byref(ctypes.c_int(color_ref)), 4
        )
    except Exception:
        pass


def set_window_curvature(w, preference=DWMWCP_ROUND):
    hwnd = get_hwnd(w)
    if not hwnd:
        return
    try:
        dwmapi = ctypes.windll.dwmapi
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(ctypes.c_int(preference)),
            4,
        )
    except Exception:
        pass
