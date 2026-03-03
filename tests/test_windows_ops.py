import sys
import pytest
from unittest.mock import MagicMock, patch
from pytron.platforms.windows_ops import window, system, constants

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only tests")


# Mock the Rust bindings so we test the ctypes fallback cleanly
@pytest.fixture(autouse=True)
def mock_pytron_os():
    # Use a mock that will be returned when 'pytron.dependencies' is imported
    mock_lib = MagicMock()
    mock_os = MagicMock()
    mock_lib.pytron_os = mock_os

    # We want to test the FALLBACK to ctypes in these tests
    # so we make the Rust calls fail.
    mock_os.minimize.side_effect = Exception("Fallback")
    mock_os.close.side_effect = Exception("Fallback")
    mock_os.set_always_on_top.side_effect = Exception("Fallback")
    mock_os.show.side_effect = Exception("Fallback")
    mock_os.hide.side_effect = Exception("Fallback")

    with patch.dict(sys.modules, {"pytron.dependencies": mock_lib}):
        yield mock_os


@pytest.fixture(autouse=True)
def mock_hwnd_window():
    with patch("pytron.platforms.windows_ops.window.get_hwnd", return_value=12345) as m:
        yield m


@pytest.fixture(autouse=True)
def mock_hwnd_system():
    with patch("pytron.platforms.windows_ops.system.get_hwnd", return_value=12345) as m:
        yield m


def test_window_minimize(mock_hwnd_window):
    with patch.object(window.user32, "ShowWindow") as mock_show:
        window.minimize("dummy_w")
        mock_show.assert_called_with(12345, constants.SW_MINIMIZE)


def test_window_close(mock_hwnd_window):
    with patch.object(window.user32, "PostMessageW") as mock_post:
        window.close("dummy_w")
        mock_post.assert_called_with(12345, constants.WM_CLOSE, 0, 0)


def test_system_notification(mock_hwnd_system):
    with patch.object(
        system.shell32, "Shell_NotifyIconW", return_value=1
    ) as mock_notify:
        # We also need to mock LoadImageW and LoadIconW to avoid crashes or failures
        with patch.object(system.user32, "LoadImageW", return_value=999), patch.object(
            system.user32, "LoadIconW", return_value=888
        ):
            system.notification("dummy_w", "Title", "Message")
            assert mock_notify.call_count >= 1


def test_system_message_box(mock_hwnd_system):
    with patch.object(system.user32, "MessageBoxW", return_value=1) as mock_msg:
        ret = system.message_box("dummy_w", "Title", "Msg", 0)
        assert ret == 1
        mock_msg.assert_called_with(12345, "Msg", "Title", 0)


def test_window_set_always_on_top(mock_hwnd_window):
    with patch.object(window.user32, "SetWindowPos") as mock_swp:
        window.set_always_on_top("dummy_w", True)
        # HWND_TOPMOST = -1
        # Flags: SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE = 0x0002 | 0x0001 | 0x0010 = 0x0013 (19)
        mock_swp.assert_called_with(12345, -1, 0, 0, 0, 0, 19)


def test_window_set_fullscreen(mock_hwnd_window):
    # Mock return values for complex ctypes calls
    with patch.object(window.user32, "GetWindowRect") as mock_gwr, patch.object(
        window.user32, "GetWindowLongW", return_value=0
    ) as mock_gwl, patch.object(
        window.user32, "MonitorFromWindow"
    ) as mock_mfw, patch.object(
        window.user32, "GetMonitorInfoW"
    ) as mock_gmi, patch.object(
        window.user32, "SetWindowLongW"
    ) as mock_swl, patch.object(
        window.user32, "SetWindowPos"
    ) as mock_swp:

        window.set_fullscreen("dummy_w", True)
        assert mock_swl.called
        assert mock_swp.called
