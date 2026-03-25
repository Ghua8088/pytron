def get_hwnd(w):
    # If w is already an integer (HWND), return it.
    if isinstance(w, int):
        return w
    # If w is a Webview instance, return its hwnd property.
    try:
        return w.hwnd
    except AttributeError:
        # Fallback for mock objects in tests or other window-like objects
        return getattr(w, "native", 0)
