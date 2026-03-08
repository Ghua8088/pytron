import time
import pytest

# pytron_os is a native binary (.so/.pyd) that requires platform libs like GTK on Linux.
# Skip the whole module if it can't be loaded (e.g. headless CI with no GTK).
pytron_os = pytest.importorskip(
    "pytron.dependencies.pytron_os",
    reason="pytron_os native binary unavailable (missing system libs or not built)",
)


def test_clipboard_integrity():
    test_text = f"Pytron Rust Clipboard Test {time.time()}"
    success = pytron_os.set_clipboard_text(test_text)
    assert success, "Could not set clipboard"

    retrieved = pytron_os.get_clipboard_text()
    assert (
        retrieved == test_text
    ), f"Clipboard mismatch: expected {test_text}, got {retrieved}"
