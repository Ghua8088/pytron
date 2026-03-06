"""Tests for NativeMixin (pytron.apputils.native)."""

import sys
import platform
import pytest
from unittest.mock import MagicMock, patch, call
from pytron.apputils.native import NativeMixin


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class MockApp(NativeMixin):
    def __init__(self):
        self.config = {"title": "Test App", "author": "Me"}
        self.windows = []
        self.logger = MagicMock()


@pytest.fixture
def app():
    return MockApp()


@pytest.fixture
def app_with_window():
    a = MockApp()
    a.windows.append(MagicMock())
    return a


# ---------------------------------------------------------------------------
# set_start_on_boot — dev mode guard
# ---------------------------------------------------------------------------

def test_set_start_on_boot_dev_mode_returns_false(app):
    """Not frozen → always skip without touching OS."""
    with patch("sys.frozen", False, create=True):
        result = app.set_start_on_boot(True)
    assert result is False


def test_set_start_on_boot_dev_mode_never_calls_pytron_os(app):
    mock_os = MagicMock()
    with patch("sys.frozen", False, create=True):
        with patch("pytron.apputils.native.pytron_os", mock_os):
            app.set_start_on_boot(True)
    mock_os.set_launch_on_boot.assert_not_called()


# ---------------------------------------------------------------------------
# set_start_on_boot — pytron_os (Rust) path
# ---------------------------------------------------------------------------

def test_set_start_on_boot_via_pytron_os(app):
    """Rust path succeeds → returns True, correct args forwarded."""
    mock_os = MagicMock()
    mock_os.set_launch_on_boot.return_value = True
    with patch("sys.frozen", True, create=True):
        with patch("pytron.apputils.native.pytron_os", mock_os):
            result = app.set_start_on_boot(True)
    assert result is True
    mock_os.set_launch_on_boot.assert_called_once_with("Test_App", sys.executable, True)


def test_set_start_on_boot_pytron_os_enable_false(app):
    mock_os = MagicMock()
    mock_os.set_launch_on_boot.return_value = True
    with patch("sys.frozen", True, create=True):
        with patch("pytron.apputils.native.pytron_os", mock_os):
            app.set_start_on_boot(False)
    assert mock_os.set_launch_on_boot.call_args[0][2] is False


def test_set_start_on_boot_safe_name_sanitisation(app):
    """Spaces / special chars in title are replaced with '_'."""
    app.config["title"] = "My Awesome App!"
    mock_os = MagicMock()
    mock_os.set_launch_on_boot.return_value = True
    with patch("sys.frozen", True, create=True):
        with patch("pytron.apputils.native.pytron_os", mock_os):
            app.set_start_on_boot(True)
    assert mock_os.set_launch_on_boot.call_args[0][0] == "My_Awesome_App_"


# ---------------------------------------------------------------------------
# set_start_on_boot — platform fallback (pytron_os absent / returns False)
# ---------------------------------------------------------------------------

def test_set_start_on_boot_windows_fallback_when_pytron_os_none(app):
    """pytron_os=None → Windows impl is called."""
    with patch("sys.frozen", True, create=True):
        with patch("pytron.apputils.native.pytron_os", None):
            with patch("platform.system", return_value="Windows"):
                with patch("pytron.platforms.windows.WindowsImplementation") as MockWin:
                    MockWin.return_value.set_launch_on_boot.return_value = True
                    result = app.set_start_on_boot(True)
    MockWin.return_value.set_launch_on_boot.assert_called_once()
    assert result is True


def test_set_start_on_boot_windows_fallback_args(app):
    """Windows impl receives sanitised name, exe path, and enable flag."""
    with patch("sys.frozen", True, create=True):
        with patch("pytron.apputils.native.pytron_os", None):
            with patch("platform.system", return_value="Windows"):
                with patch("pytron.platforms.windows.WindowsImplementation") as MockWin:
                    MockWin.return_value.set_launch_on_boot.return_value = True
                    app.set_start_on_boot(False)
    args = MockWin.return_value.set_launch_on_boot.call_args[0]
    assert args[0] == "Test_App"
    assert args[2] is False


def test_set_start_on_boot_falls_through_when_pytron_os_returns_false(app):
    """pytron_os returns False → platform fallback is tried."""
    mock_os = MagicMock()
    mock_os.set_launch_on_boot.return_value = False
    with patch("sys.frozen", True, create=True):
        with patch("pytron.apputils.native.pytron_os", mock_os):
            with patch("platform.system", return_value="Windows"):
                with patch("pytron.platforms.windows.WindowsImplementation") as MockWin:
                    MockWin.return_value.set_launch_on_boot.return_value = True
                    result = app.set_start_on_boot(True)
    MockWin.return_value.set_launch_on_boot.assert_called_once()
    assert result is True


def test_set_start_on_boot_falls_through_when_pytron_os_raises(app):
    """pytron_os raises → silently falls through, no exception propagated."""
    mock_os = MagicMock()
    mock_os.set_launch_on_boot.side_effect = RuntimeError("no pyd")
    with patch("sys.frozen", True, create=True):
        with patch("pytron.apputils.native.pytron_os", mock_os):
            with patch("platform.system", return_value="Windows"):
                with patch("pytron.platforms.windows.WindowsImplementation") as MockWin:
                    MockWin.return_value.set_launch_on_boot.return_value = True
                    result = app.set_start_on_boot(True)  # must not raise
    MockWin.return_value.set_launch_on_boot.assert_called_once()


def test_set_start_on_boot_linux_fallback(app):
    with patch("sys.frozen", True, create=True):
        with patch("pytron.apputils.native.pytron_os", None):
            with patch("platform.system", return_value="Linux"):
                with patch("pytron.platforms.linux.LinuxImplementation") as MockLin:
                    MockLin.return_value.set_launch_on_boot.return_value = True
                    result = app.set_start_on_boot(True)
    MockLin.return_value.set_launch_on_boot.assert_called_once()
    assert result is True


def test_set_start_on_boot_darwin_fallback(app):
    with patch("sys.frozen", True, create=True):
        with patch("pytron.apputils.native.pytron_os", None):
            with patch("platform.system", return_value="Darwin"):
                with patch("pytron.platforms.darwin.DarwinImplementation") as MockDarwin:
                    MockDarwin.return_value.set_launch_on_boot.return_value = True
                    result = app.set_start_on_boot(True)
    MockDarwin.return_value.set_launch_on_boot.assert_called_once()
    assert result is True


def test_set_start_on_boot_unknown_platform_returns_false(app):
    with patch("sys.frozen", True, create=True):
        with patch("pytron.apputils.native.pytron_os", None):
            with patch("platform.system", return_value="FreeBSD"):
                result = app.set_start_on_boot(True)
    assert result is False


def test_set_start_on_boot_no_window_delegation(app):
    """NativeMixin must NOT delegate to an open window's _platform."""
    mock_window = MagicMock()
    app.windows.append(mock_window)
    with patch("sys.frozen", True, create=True):
        with patch("pytron.apputils.native.pytron_os", None):
            with patch("platform.system", return_value="Windows"):
                with patch("pytron.platforms.windows.WindowsImplementation"):
                    app.set_start_on_boot(True)
    mock_window._platform.set_launch_on_boot.assert_not_called()


# ---------------------------------------------------------------------------
# message_box
# ---------------------------------------------------------------------------

def test_message_box_delegates_to_first_window(app_with_window):
    app_with_window.message_box("Title", "Msg")
    app_with_window.windows[0].message_box.assert_called_with("Title", "Msg", 0)


def test_message_box_forwards_style(app_with_window):
    app_with_window.message_box("T", "M", style=4)
    app_with_window.windows[0].message_box.assert_called_with("T", "M", 4)


def test_message_box_returns_window_result(app_with_window):
    app_with_window.windows[0].message_box.return_value = 6
    assert app_with_window.message_box("T", "M") == 6


def test_message_box_returns_zero_without_window(app):
    assert app.message_box("T", "M") == 0


# ---------------------------------------------------------------------------
# dialogs
# ---------------------------------------------------------------------------

def test_dialog_save_file_delegates(app_with_window):
    app_with_window.dialog_save_file("Save")
    app_with_window.windows[0].dialog_save_file.assert_called()


def test_dialog_save_file_passes_kwargs(app_with_window):
    app_with_window.dialog_save_file("S", default_path="/tmp", default_name="out.txt")
    app_with_window.windows[0].dialog_save_file.assert_called_with(
        "S", "/tmp", "out.txt", None
    )


def test_dialog_save_file_returns_none_without_window(app):
    assert app.dialog_save_file("Save") is None


def test_dialog_open_file_delegates(app_with_window):
    app_with_window.dialog_open_file("Open")
    app_with_window.windows[0].dialog_open_file.assert_called()


def test_dialog_open_file_returns_none_without_window(app):
    assert app.dialog_open_file("Open") is None


def test_dialog_open_folder_delegates(app_with_window):
    app_with_window.dialog_open_folder("Folder")
    app_with_window.windows[0].dialog_open_folder.assert_called()


def test_dialog_open_folder_returns_none_without_window(app):
    assert app.dialog_open_folder("Folder") is None


# ---------------------------------------------------------------------------
# system_notification
# ---------------------------------------------------------------------------

def test_system_notification_delegates(app_with_window):
    app_with_window.config["icon"] = "icon.ico"
    app_with_window.system_notification("Title", "Body")
    app_with_window.windows[0].system_notification.assert_called_with(
        "Title", "Body", icon="icon.ico"
    )


def test_system_notification_default_title_from_author(app_with_window):
    app_with_window.system_notification(message="Body")
    args = app_with_window.windows[0].system_notification.call_args[0]
    assert args[0] == "Me"


def test_system_notification_default_title_fallback_to_app_title(app_with_window):
    del app_with_window.config["author"]
    app_with_window.system_notification(message="Body")
    args = app_with_window.windows[0].system_notification.call_args[0]
    assert args[0] == "Test App"


def test_system_notification_no_icon_by_default(app_with_window):
    app_with_window.system_notification("T", "B")
    app_with_window.windows[0].system_notification.assert_called_with(
        "T", "B", icon=None
    )


def test_system_notification_silent_when_no_window(app):
    app.system_notification("T", "B")  # must not raise


def test_system_notification_stops_after_first_success(app):
    w1, w2 = MagicMock(), MagicMock()
    app.windows = [w1, w2]
    app.system_notification("T", "B")
    w1.system_notification.assert_called_once()
    w2.system_notification.assert_not_called()


def test_system_notification_tries_next_window_on_exception(app):
    w1, w2 = MagicMock(), MagicMock()
    w1.system_notification.side_effect = RuntimeError("gone")
    app.windows = [w1, w2]
    app.system_notification("T", "B")
    w2.system_notification.assert_called_once()


# ---------------------------------------------------------------------------
# show_toast
# ---------------------------------------------------------------------------

def test_show_toast_delegates(app_with_window):
    cfg = {"title": "Hello", "body": "World"}
    app_with_window.show_toast(cfg)
    app_with_window.windows[0].toast.assert_called_with(cfg)


def test_show_toast_silent_when_no_window(app):
    app.show_toast({"title": "T", "body": "B"})  # must not raise


def test_show_toast_stops_after_first_success(app):
    w1, w2 = MagicMock(), MagicMock()
    app.windows = [w1, w2]
    app.show_toast({})
    w1.toast.assert_called_once()
    w2.toast.assert_not_called()


# ---------------------------------------------------------------------------
# clipboard
# ---------------------------------------------------------------------------

def test_copy_to_clipboard_delegates(app_with_window):
    app_with_window.windows[0]._platform.set_clipboard_text.return_value = True
    result = app_with_window.copy_to_clipboard("hello")
    app_with_window.windows[0]._platform.set_clipboard_text.assert_called_with("hello")
    assert result is True


def test_copy_to_clipboard_returns_false_without_window(app):
    assert app.copy_to_clipboard("x") is False


def test_get_clipboard_text_delegates(app_with_window):
    app_with_window.windows[0]._platform.get_clipboard_text.return_value = "hi"
    assert app_with_window.get_clipboard_text() == "hi"


def test_get_clipboard_text_returns_none_without_window(app):
    assert app.get_clipboard_text() is None


# ---------------------------------------------------------------------------
# get_system_info
# ---------------------------------------------------------------------------

def test_get_system_info_delegates(app_with_window):
    app_with_window.windows[0]._platform.get_system_info.return_value = {"os": "Windows"}
    assert app_with_window.get_system_info() == {"os": "Windows"}


def test_get_system_info_fallback_without_window(app):
    info = app.get_system_info()
    assert "os" in info
    assert "arch" in info
    assert isinstance(info["os"], str)
