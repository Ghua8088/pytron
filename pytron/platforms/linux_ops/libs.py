import ctypes

gtk = None
webkit = None
glib = None
gio = None


def load_libs():
    global gtk, webkit, glib, gio

    import sys
    import os

    # On Linux, core libraries MUST be loaded with RTLD_GLOBAL
    # so that native modules (Rust) share the same global symbols (like GType registry).
    mode = ctypes.RTLD_GLOBAL
    if hasattr(ctypes, "RTLD_NOW"):
        mode |= ctypes.RTLD_NOW

    # --- NATIVE SCHISM GUARD ---
    # If using Native Engine, the Rust process OWNS the GTK context.
    # Independent ctypes loading of GLib/GIO can cause "cannot register existing type" crashes.
    if os.environ.get("PYTRON_ENGINE") == "native" and sys.platform.startswith("linux"):
        # We only proceed if we are being called explicitly or if there's no choice.
        # For now, let's satisfy the Schism by NOT loading unless strictly necessary.
        return

    # Load GTK
    if not gtk:
        for name in ["libgtk-3.so.0", "libgtk-3.so"]:
            try:
                gtk = ctypes.CDLL(name, mode=mode)
                break
            except OSError:
                continue

    # Load WebKit
    if not webkit:
        for name in ["libwebkit2gtk-4.1.so.0", "libwebkit2gtk-4.0.so.37"]:
            try:
                webkit = ctypes.CDLL(name, mode=mode)
                break
            except OSError:
                continue

    # Load GLib
    if not glib:
        try:
            glib = ctypes.CDLL("libglib-2.0.so.0", mode=mode)
        except OSError:
            pass

    # Load Gio
    if not gio:
        try:
            gio = ctypes.CDLL("libgio-2.0.so.0", mode=mode)
        except OSError:
            pass


# Lazy initialization is preferred on Linux
# We no longer call load_libs() globally here to prevent the Schism during import.
