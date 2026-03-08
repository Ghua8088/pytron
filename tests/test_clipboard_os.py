import time
from pytron.dependencies import pytron_os


def test_clipboard_integrity():
    test_text = f"Pytron Rust Clipboard Test {time.time()}"
    success = pytron_os.set_clipboard_text(test_text)
    assert success, "Could not set clipboard"

    retrieved = pytron_os.get_clipboard_text()
    assert (
        retrieved == test_text
    ), f"Clipboard mismatch: expected {test_text}, got {retrieved}"
