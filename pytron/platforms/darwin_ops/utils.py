import ctypes
from ...bindings import lib
from . import libs


def get_window(w):
    return lib.webview_get_window(w)


def msg_send(target, selector, *args, restype=ctypes.c_void_p, argtypes=None):
    if not libs.objc:
        return None
    
    # Safety: If we are in a test environment with Mocks, avoid CFUNCTYPE casting
    # on the mock as it can cause infinite recursion during internal ctypes inspection.
    from unittest.mock import Mock
    if isinstance(libs.objc, Mock):
        # In mock mode, just call directly to record the call
        return libs.objc.objc_msgSend(target, selector, *args)

    # On macOS ARM64, objc_msgSend MUST be cast to the correct function pointer type
    # before being called, or it will cause a segmentation fault.
    if argtypes is None:
        # Infer from args
        argtypes = []
        for x in args:
            if isinstance(x, (int, float, bool)):
                if isinstance(x, bool):
                     argtypes.append(ctypes.c_bool)
                elif isinstance(x, float):
                     argtypes.append(ctypes.c_double)
                else:
                     argtypes.append(ctypes.c_void_p)
            else:
                argtypes.append(ctypes.c_void_p)

    all_argtypes = [ctypes.c_void_p, ctypes.c_void_p] + list(argtypes)
    
    # We must ensure we are using the raw function pointer without restype/argtypes 
    # already set on it, as that can interfere with CFUNCTYPE.
    try:
        # Get the underlying function pointer address
        func_addr = ctypes.cast(libs.objc.objc_msgSend, ctypes.c_void_p).value
        proto = ctypes.CFUNCTYPE(restype, *all_argtypes)
        f = proto(func_addr)
    except Exception:
        # Fallback to direct call if casting fails (though this may crash on ARM64)
        f = libs.objc.objc_msgSend

    sel = libs.objc.sel_registerName(selector.encode("utf-8"))
    return f(target, sel, *args)


def call(obj, selector, *args):
    # Backward compatible call - defaults to void_p return
    return msg_send(obj, selector, *args)


def get_class(name):
    if not libs.objc:
        return None
    return libs.objc.objc_getClass(name.encode("utf-8"))


def str_to_nsstring(s):
    if not libs.objc:
        return None
    cls = get_class("NSString")
    sel = libs.objc.sel_registerName("stringWithUTF8String:".encode("utf-8"))
    f = ctypes.CFUNCTYPE(
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p
    )(libs.objc.objc_msgSend)
    return f(cls, sel, s.encode("utf-8"))


def bool_to_nsnumber(b):
    if not libs.objc:
        return None
    cls = get_class("NSNumber")
    sel = libs.objc.sel_registerName("numberWithBool:".encode("utf-8"))
    f = ctypes.CFUNCTYPE(
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool
    )(libs.objc.objc_msgSend)
    return f(cls, sel, b)
