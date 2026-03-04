import sys
import pytest
from unittest.mock import MagicMock, patch
from pytron.apputils.native import NativeMixin


class MockApp(NativeMixin):
    def __init__(self):
        self.config = {"title": "Test App", "author": "Me"}
        self.windows = []
        self.logger = MagicMock()


@pytest.fixture
def app():
    return MockApp()


def test_set_start_on_boot_windows(app):
    with patch("sys.platform", "win32"):
        with patch("platform.system", return_value="Windows"):
            with patch("pytron.platforms.windows.WindowsImplementation") as MockWin:
                with patch("sys.frozen", True, create=True):
                    # Set to None in sys.modules to force ImportError on "from ... import pytron_os"
                    with patch.dict(
                        "sys.modules", {"pytron.dependencies.pytron_os": None}
                    ):
                        mock_impl = MockWin.return_value
                        app.set_start_on_boot(True)
                        mock_impl.set_launch_on_boot.assert_called()
                        args = mock_impl.set_launch_on_boot.call_args[0]
                        assert args[0] == "Test_App"  # Safe name
                        assert args[2] is True  # Enable


def test_set_start_on_boot_pytron_os(app):
    with patch("sys.frozen", True, create=True):
        mock_os = MagicMock()
        mock_os.set_launch_on_boot.return_value = True
        # Patch BOTH sys.modules and the target in native.py
        with patch.dict("sys.modules", {"pytron.dependencies.pytron_os": mock_os}):
            with patch("pytron.apputils.native.pytron_os", mock_os, create=True):
                app.set_start_on_boot(True)
                mock_os.set_launch_on_boot.assert_called_with(
                    "Test_App", sys.executable, True
                )


def test_set_start_on_boot_no_delegation(app):
    mock_window = MagicMock()
    app.windows.append(mock_window)

    with patch("sys.platform", "win32"):
        with patch("platform.system", return_value="Windows"):
            with patch("pytron.platforms.windows.WindowsImplementation") as MockWin:
                with patch("sys.frozen", True, create=True):
                    with patch.dict(
                        "sys.modules", {"pytron.dependencies.pytron_os": None}
                    ):
                        app.set_start_on_boot(False)

                        # Delegation to window is gone, should call WindowsImplementation directly
                        MockWin.return_value.set_launch_on_boot.assert_called()
                        # Window's platform should NOT be called directly by NativeMixin
                        mock_window._platform.set_launch_on_boot.assert_not_called()


def test_dialog_delegation(app):
    # These methods just delegate to the first window
    mock_window = MagicMock()
    app.windows.append(mock_window)

    app.message_box("Title", "Msg")
    mock_window.message_box.assert_called_with("Title", "Msg", 0)

    app.dialog_save_file("Save")
    mock_window.dialog_save_file.assert_called()

    app.dialog_open_file("Open")
    mock_window.dialog_open_file.assert_called()

    app.dialog_open_folder("Folder")
    mock_window.dialog_open_folder.assert_called()


def test_dialog_no_window(app):
    # Should return default values if no window
    assert app.message_box("T", "M") == 0
    assert app.dialog_save_file("S") is None
    assert app.dialog_open_file("O") is None
    assert app.dialog_open_folder("F") is None


def test_system_notification(app):
    mock_window = MagicMock()
    app.windows.append(mock_window)
    app.config["icon"] = "icon.ico"

    app.system_notification("Title", "Body")

    mock_window.system_notification.assert_called_with("Title", "Body", icon="icon.ico")


def test_system_notification_defaults(app):
    mock_window = MagicMock()
    app.windows.append(mock_window)

    app.system_notification(message="Body")

    # Should use author/title from config as title
    args = mock_window.system_notification.call_args[0]
    assert args[0] == "Me"  # Author
