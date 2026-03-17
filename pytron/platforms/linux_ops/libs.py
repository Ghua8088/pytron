import ctypes
import os
import sys

# These handles will now remain None on Linux when using Native Engine.
# This prevents the GObject type registration conflict (The Schism).
gtk = None
webkit = None
glib = None
gio = None


def load_libs():
    """
    On Linux, we explicitly avoid loading these via ctypes if the native engine is active.
    This architecture ensures that the Rust Native Engine is the SOLE owner of the
    GObject/GTK context, preventing 'cannot register existing type' crashes.
    """
    global gtk, webkit, glib, gio

    # Only allow ctypes loading on Linux if we are NOT in a native engine context.
    # This preserves functionality for the legacy 'chrome' or 'servo' engines.
    engine = os.environ.get("PYTRON_ENGINE", "native")
    if sys.platform.startswith("linux") and engine == "native":
        if os.environ.get("PYTRON_DEBUG_SCHISM") == "1":
            print(
                f"[Pytron Debug] libs.load_libs: SKIPPING ctype load (Engine: {engine}) to prevent Schism."
            )
        return

    if os.environ.get("PYTRON_DEBUG_SCHISM") == "1":
        print(
            f"[Pytron Debug] libs.load_libs: PROCEEDING with ctype load (Engine: {engine})."
        )

    # Fallback for non-native engines (Legacy support)
    mode = ctypes.RTLD_GLOBAL
    if hasattr(ctypes, "RTLD_NOW"):
        mode |= ctypes.RTLD_NOW

    try:
        if not gtk:
            gtk = ctypes.CDLL("libgtk-3.so.0", mode=mode)
        if not webkit:
            webkit = ctypes.CDLL("libwebkit2gtk-4.1.so.0", mode=mode)
        if not glib:
            glib = ctypes.CDLL("libglib-2.0.so.0", mode=mode)
        if not gio:
            gio = ctypes.CDLL("libgio-2.0.so.0", mode=mode)
    except OSError:
        pass
