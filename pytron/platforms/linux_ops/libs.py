import ctypes

gtk = None
webkit = None
glib = None
gio = None


def load_libs():
    global gtk, webkit, glib, gio

    # --- GLIB SCHISM GUARD ---
    # In Native Engine mode, the Rust extension handles its own GTK/GObject linking.
    # We must skip ctypes loading of these libraries to avoid symbol collisions.
    import os
    import sys

    engine = os.environ.get("PYTRON_ENGINE", "native")  # Default to native if unknown
    if engine == "native" and sys.platform.startswith("linux"):
        return

    # Load GTK
    if not gtk:
        try:
            gtk = ctypes.CDLL("libgtk-3.so.0")
        except OSError:
            try:
                gtk = ctypes.CDLL("libgtk-3.so")
            except OSError:
                pass

    # Load WebKit
    if not webkit:
        try:
            webkit = ctypes.CDLL("libwebkit2gtk-4.1.so.0")
        except OSError:
            try:
                webkit = ctypes.CDLL("libwebkit2gtk-4.0.so.37")
            except OSError:
                pass

    # Load GLib
    if not glib:
        try:
            glib = ctypes.CDLL("libglib-2.0.so.0")
        except OSError:
            pass

    # Load Gio
    if not gio:
        try:
            gio = ctypes.CDLL("libgio-2.0.so.0")
        except OSError:
            pass


# Initialize on import? Or let the facade call it?
# Let's initialize on import for simplicity, or lazily.
load_libs()
