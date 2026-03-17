import time
import pytest

# pytron_os is a native binary (.so/.pyd) that requires platform libs like GTK on Linux.
# Skip the whole module if it can't be loaded (e.g. headless CI with no GTK).
pytron_os = pytest.importorskip(
    "pytron.dependencies.pytron_os",
    reason="pytron_os native binary unavailable (missing system libs or not built)",
)


def test_clipboard_integrity():
    import sys
    import time

    test_text = f"Pytron Rust Clipboard Test {time.time()}"

    if sys.platform == "linux":
        # On Linux, use the system helper which has xclip/xsel fallbacks
        from pytron.platforms.linux_ops import system

        success = system.set_clipboard_text(test_text)
        assert success, "Could not set clipboard via system layer"
        retrieved = system.get_clipboard_text()
    else:
        # On Windows/Mac, use the native module directly
        success = pytron_os.set_clipboard_text(test_text)
        assert success, "Could not set clipboard via native binary"
        retrieved = pytron_os.get_clipboard_text()

    assert (
        retrieved == test_text
    ), f"Clipboard mismatch: expected {test_text}, got {retrieved}"
