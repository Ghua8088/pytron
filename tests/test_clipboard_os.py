import time


def test_clipboard_integrity():
    import sys
    import time

    test_text = f"Pytron Rust Clipboard Test {time.time()}"

    if sys.platform == "linux":
        from pytron.platforms.linux_ops import system

        success = system.set_clipboard_text(test_text)
        assert success, "Could not set clipboard via system layer"
        retrieved = system.get_clipboard_text()
    elif sys.platform == "win32":
        from pytron.platforms.windows_ops import system

        success = system.set_clipboard_text(test_text)
        assert success, "Could not set clipboard via Windows bridge"
        retrieved = system.get_clipboard_text()
    elif sys.platform == "darwin":
        from pytron.platforms.darwin import DarwinImplementation

        impl = DarwinImplementation()
        success = impl.set_clipboard_text(test_text)
        assert success, "Could not set clipboard via macOS bridge"
        retrieved = impl.get_clipboard_text()
    else:
        raise AssertionError(f"Unsupported platform for clipboard test: {sys.platform}")

    assert (
        retrieved == test_text
    ), f"Clipboard mismatch: expected {test_text}, got {retrieved}"
