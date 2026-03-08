import sys
import ctypes
import pytest
from unittest.mock import MagicMock, patch, call
from pytron.platforms.windows_ops import window, system, constants

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only tests")

# The real pytron_os is bound at import time in window.py / system.py.
# Patching sys.modules after the fact has no effect on already-bound names.
# We must patch the module-level variable directly.
WIN_OS = "pytron.platforms.windows_ops.window.pytron_os"
SYS_OS = "pytron.platforms.windows_ops.system.pytron_os"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hwnd_window():
    """Patch get_hwnd in the window module to return a known value."""
    with patch("pytron.platforms.windows_ops.window.get_hwnd", return_value=12345) as m:
        yield m


@pytest.fixture
def hwnd_system():
    """Patch get_hwnd in the system module to return a known value."""
    with patch("pytron.platforms.windows_ops.system.get_hwnd", return_value=12345) as m:
        yield m


@pytest.fixture
def no_pytron_os_window():
    """Force the ctypes fallback path in window.py."""
    with patch(WIN_OS, None):
        yield


@pytest.fixture
def no_pytron_os_system():
    """Force the ctypes fallback path in system.py."""
    with patch(SYS_OS, None):
        yield


# ---------------------------------------------------------------------------
# window.minimize
# ---------------------------------------------------------------------------


def test_window_minimize_ctypes(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "ShowWindow") as mock_show:
        window.minimize("w")
        mock_show.assert_called_with(12345, constants.SW_MINIMIZE)


def test_window_minimize_rust_path(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.minimize("w")
        mock_os.minimize.assert_called_with(12345)


def test_window_minimize_rust_fallback_to_ctypes(hwnd_window):
    mock_os = MagicMock()
    mock_os.minimize.side_effect = RuntimeError("fail")
    with patch(WIN_OS, mock_os), patch.object(window.user32, "ShowWindow") as mock_show:
        window.minimize("w")
        mock_show.assert_called_with(12345, constants.SW_MINIMIZE)


def test_window_minimize_noop_when_no_hwnd():
    with patch("pytron.platforms.windows_ops.window.get_hwnd", return_value=0), patch(
        WIN_OS, None
    ), patch.object(window.user32, "ShowWindow") as mock_show:
        window.minimize("w")
        mock_show.assert_not_called()


# ---------------------------------------------------------------------------
# window.close
# ---------------------------------------------------------------------------


def test_window_close_ctypes(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "PostMessageW") as mock_post:
        window.close("w")
        mock_post.assert_called_with(12345, constants.WM_CLOSE, 0, 0)


def test_window_close_rust_path(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.close("w")
        mock_os.close.assert_called_with(12345)


def test_window_close_rust_fallback(hwnd_window):
    mock_os = MagicMock()
    mock_os.close.side_effect = RuntimeError("fail")
    with patch(WIN_OS, mock_os), patch.object(
        window.user32, "PostMessageW"
    ) as mock_post:
        window.close("w")
        mock_post.assert_called_with(12345, constants.WM_CLOSE, 0, 0)


def test_window_close_noop_when_no_hwnd():
    with patch("pytron.platforms.windows_ops.window.get_hwnd", return_value=0), patch(
        WIN_OS, None
    ), patch.object(window.user32, "PostMessageW") as mock_post:
        window.close("w")
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# window.show / hide
# ---------------------------------------------------------------------------


def test_window_show_ctypes(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "ShowWindow") as mock_sw, patch.object(
        window.user32, "SetForegroundWindow"
    ):
        window.show("w")
        mock_sw.assert_called_with(12345, constants.SW_SHOW)


def test_window_hide_ctypes(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "ShowWindow") as mock_sw:
        window.hide("w")
        mock_sw.assert_called_with(12345, constants.SW_HIDE)


def test_window_show_rust_path(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.show("w")
        mock_os.show.assert_called_with(12345)


def test_window_hide_rust_path(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.hide("w")
        mock_os.hide.assert_called_with(12345)


# ---------------------------------------------------------------------------
# window.toggle_maximize
# ---------------------------------------------------------------------------


def test_toggle_maximize_maximises_when_normal(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "IsZoomed", return_value=False), patch.object(
        window.user32, "ShowWindow"
    ) as mock_sw:
        result = window.toggle_maximize("w")
        mock_sw.assert_called_with(12345, constants.SW_MAXIMIZE)
        assert result is True


def test_toggle_maximize_restores_when_maximised(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "IsZoomed", return_value=True), patch.object(
        window.user32, "ShowWindow"
    ) as mock_sw:
        result = window.toggle_maximize("w")
        mock_sw.assert_called_with(12345, constants.SW_RESTORE)
        assert result is False


# ---------------------------------------------------------------------------
# window.set_always_on_top
# ---------------------------------------------------------------------------


def test_set_always_on_top_enable_ctypes(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "SetWindowPos") as mock_swp:
        window.set_always_on_top("w", True)
        # HWND_TOPMOST=-1, flags: SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE = 0x0013 = 19
        mock_swp.assert_called_with(12345, -1, 0, 0, 0, 0, 19)


def test_set_always_on_top_disable_ctypes(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "SetWindowPos") as mock_swp:
        window.set_always_on_top("w", False)
        # HWND_NOTOPMOST=-2
        mock_swp.assert_called_with(12345, -2, 0, 0, 0, 0, 19)


def test_set_always_on_top_rust_path(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.set_always_on_top("w", True)
        mock_os.set_always_on_top.assert_called_with(12345, True)


def test_set_always_on_top_noop_when_no_hwnd():
    with patch("pytron.platforms.windows_ops.window.get_hwnd", return_value=0), patch(
        WIN_OS, None
    ), patch.object(window.user32, "SetWindowPos") as mock_swp:
        window.set_always_on_top("w", True)
        mock_swp.assert_not_called()


# ---------------------------------------------------------------------------
# window.set_fullscreen
# ---------------------------------------------------------------------------


def test_set_fullscreen_enable_calls_setwindowlongw(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "GetWindowRect"), patch.object(
        window.user32, "GetWindowLongW", return_value=0
    ), patch.object(window.user32, "SetWindowLongW") as mock_swl, patch.object(
        window.user32, "MonitorFromWindow"
    ), patch.object(
        window.user32, "GetMonitorInfoW"
    ), patch.object(
        window.user32, "SetWindowPos"
    ):
        window.set_fullscreen("w", True)
        assert mock_swl.called


def test_set_fullscreen_enable_calls_setwindowpos(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "GetWindowRect"), patch.object(
        window.user32, "GetWindowLongW", return_value=0
    ), patch.object(window.user32, "SetWindowLongW"), patch.object(
        window.user32, "MonitorFromWindow"
    ), patch.object(
        window.user32, "GetMonitorInfoW"
    ), patch.object(
        window.user32, "SetWindowPos"
    ) as mock_swp:
        window.set_fullscreen("w", True)
        assert mock_swp.called


def test_set_fullscreen_disable_restores_style(hwnd_window, no_pytron_os_window):
    # Pre-populate storage so disable path has data to restore
    from pytron.platforms.windows_ops.window import _fullscreen_storage

    _fullscreen_storage[12345] = {"style": 0xCF0000, "rect": (0, 0, 1920, 1080)}

    with patch.object(window.user32, "SetWindowLongW") as mock_swl, patch.object(
        window.user32, "SetWindowPos"
    ) as mock_swp:
        window.set_fullscreen("w", False)
        assert mock_swl.called
        assert mock_swp.called
        assert 12345 not in _fullscreen_storage


def test_set_fullscreen_rust_path(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.set_fullscreen("w", True)
        mock_os.set_fullscreen.assert_called_with(12345, True)


def test_set_fullscreen_noop_when_no_hwnd():
    with patch("pytron.platforms.windows_ops.window.get_hwnd", return_value=0), patch(
        WIN_OS, None
    ), patch.object(window.user32, "SetWindowLongW") as mock_swl:
        window.set_fullscreen("w", True)
        mock_swl.assert_not_called()


# ---------------------------------------------------------------------------
# window.set_bounds
# ---------------------------------------------------------------------------


def test_set_bounds_ctypes(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "SetWindowPos") as mock_swp:
        window.set_bounds("w", 10, 20, 800, 600)
        mock_swp.assert_called_with(
            12345,
            0,
            10,
            20,
            800,
            600,
            constants.SWP_NOZORDER | constants.SWP_NOACTIVATE,
        )


def test_set_bounds_rust_path(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.set_bounds("w", 10, 20, 800, 600)
        mock_os.set_bounds.assert_called_with(12345, 10, 20, 800, 600)


# ---------------------------------------------------------------------------
# window.make_frameless
# ---------------------------------------------------------------------------


def test_make_frameless_strips_caption(hwnd_window, no_pytron_os_window):
    with patch.object(
        window.user32, "GetWindowLongW", return_value=0xCF0000
    ) as mock_gwl, patch.object(
        window.user32, "SetWindowLongW"
    ) as mock_swl, patch.object(
        window.user32, "SetWindowPos"
    ):
        window.make_frameless("w")
        mock_swl.assert_called()
        new_style = mock_swl.call_args[0][2]
        assert not (new_style & constants.WS_CAPTION)


# ---------------------------------------------------------------------------
# window.center
# ---------------------------------------------------------------------------


def test_center_calls_setwindowpos(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "GetWindowRect"), patch.object(
        window.user32, "GetSystemMetrics", return_value=1920
    ), patch.object(window.user32, "SetWindowPos") as mock_swp:
        window.center("w")
        assert mock_swp.called


# ---------------------------------------------------------------------------
# window.start_drag
# ---------------------------------------------------------------------------


def test_start_drag_ctypes(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "ReleaseCapture") as mock_rc, patch.object(
        window.user32, "SendMessageW"
    ) as mock_sm:
        window.start_drag("w")
        mock_rc.assert_called_once()
        mock_sm.assert_called_with(
            12345, constants.WM_NCLBUTTONDOWN, constants.HTCAPTION, 0
        )


# ---------------------------------------------------------------------------
# window.is_visible
# ---------------------------------------------------------------------------


def test_is_visible_true(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "IsWindowVisible", return_value=True):
        assert window.is_visible("w") is True


def test_is_visible_false(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "IsWindowVisible", return_value=False):
        assert window.is_visible("w") is False


def test_is_visible_returns_false_without_hwnd():
    with patch("pytron.platforms.windows_ops.window.get_hwnd", return_value=0), patch(
        WIN_OS, None
    ):
        assert window.is_visible("w") is False


# ---------------------------------------------------------------------------
# system.message_box
# ---------------------------------------------------------------------------


def test_message_box_ctypes(hwnd_system, no_pytron_os_system):
    with patch.object(system.user32, "MessageBoxW", return_value=1) as mock_mb:
        result = system.message_box("w", "Title", "Msg", 0)
        assert result == 1
        mock_mb.assert_called_with(12345, "Msg", "Title", 0)


def test_message_box_rust_path(hwnd_system):
    mock_os = MagicMock()
    mock_os.message_box.return_value = 6
    with patch(SYS_OS, mock_os):
        result = system.message_box("w", "Title", "Msg", 4)
        mock_os.message_box.assert_called_with(12345, "Title", "Msg", 4)
        assert result == 6


def test_message_box_different_styles(hwnd_system, no_pytron_os_system):
    for style in (0, 1, 4):
        with patch.object(system.user32, "MessageBoxW", return_value=1) as mock_mb:
            system.message_box("w", "T", "M", style)
            mock_mb.assert_called_with(12345, "M", "T", style)


# ---------------------------------------------------------------------------
# system.notification
# ---------------------------------------------------------------------------


def test_system_notification_ctypes_calls_shell_notify(
    hwnd_system, no_pytron_os_system
):
    with patch.object(
        system.shell32, "Shell_NotifyIconW", return_value=1
    ) as mock_notify, patch.object(
        system.user32, "LoadImageW", return_value=999
    ), patch.object(
        system.user32, "LoadIconW", return_value=888
    ):
        system.notification("w", "Title", "Message")
        assert mock_notify.call_count >= 1  # NIM_ADD + NIM_SETVERSION + NIM_MODIFY


def test_system_notification_rust_path(hwnd_system):
    mock_os = MagicMock()
    with patch(SYS_OS, mock_os):
        system.notification("w", "Title", "Msg", icon=None)
        mock_os.show_notification.assert_called()


def test_system_notification_rust_fallback_to_ctypes(hwnd_system):
    mock_os = MagicMock()
    mock_os.show_notification.side_effect = RuntimeError("fail")
    with patch(SYS_OS, mock_os), patch.object(
        system.shell32, "Shell_NotifyIconW", return_value=1
    ) as mock_notify, patch.object(
        system.user32, "LoadImageW", return_value=0
    ), patch.object(
        system.user32, "LoadIconW", return_value=888
    ):
        system.notification("w", "Title", "Msg")
        assert mock_notify.call_count >= 1


def test_system_notification_noop_when_no_hwnd(no_pytron_os_system):
    with patch(
        "pytron.platforms.windows_ops.system.get_hwnd", return_value=0
    ), patch.object(system.shell32, "Shell_NotifyIconW") as mock_notify:
        system.notification("w", "Title", "Msg")
        mock_notify.assert_not_called()


# ---------------------------------------------------------------------------
# system.set_window_icon
# ---------------------------------------------------------------------------


def test_set_window_icon_rust_path(hwnd_system):
    mock_os = MagicMock()
    with patch(SYS_OS, mock_os), patch("os.path.exists", return_value=True):
        system.set_window_icon("w", "/fake/icon.ico")
        mock_os.set_window_icon.assert_called()


def test_set_window_icon_skips_missing_file(hwnd_system, no_pytron_os_system):
    with patch.object(system.user32, "LoadImageW") as mock_load:
        system.set_window_icon("w", "/nonexistent/icon.ico")
        mock_load.assert_not_called()


def test_set_window_icon_ctypes_sends_wm_seticon(hwnd_system, no_pytron_os_system):
    import tempfile, os

    with tempfile.NamedTemporaryFile(suffix=".ico", delete=False) as f:
        ico_path = f.name
    try:
        with patch.object(
            system.user32, "LoadImageW", return_value=999
        ) as mock_li, patch.object(system.user32, "SendMessageW") as mock_sm:
            system.set_window_icon("w", ico_path)
            assert mock_sm.called
    finally:
        os.unlink(ico_path)


# ---------------------------------------------------------------------------
# system.open_file_dialog
# ---------------------------------------------------------------------------


def test_open_file_dialog_ctypes_calls_getopenfn(hwnd_system, no_pytron_os_system):
    with patch.object(
        system.comdlg32, "GetOpenFileNameW", return_value=False
    ) as mock_gof:
        result = system.open_file_dialog("w", "Open")
        assert result is None
        mock_gof.assert_called_once()


def test_open_file_dialog_rust_path(hwnd_system):
    mock_os = MagicMock()
    mock_os.open_file_dialog.return_value = "/chosen/file.txt"
    with patch(SYS_OS, mock_os):
        result = system.open_file_dialog("w", "Open")
        assert result == "/chosen/file.txt"


# ---------------------------------------------------------------------------
# system.save_file_dialog
# ---------------------------------------------------------------------------


def test_save_file_dialog_rust_path(hwnd_system):
    mock_os = MagicMock()
    mock_os.save_file_dialog.return_value = "/out/file.csv"
    with patch(SYS_OS, mock_os):
        result = system.save_file_dialog("w", "Save", "/out", "file.csv")
        assert result == "/out/file.csv"


def test_save_file_dialog_rust_returns_none_falls_through(
    hwnd_system, no_pytron_os_system
):
    with patch.object(
        system.comdlg32, "GetSaveFileNameW", return_value=False
    ) as mock_gsf:
        result = system.save_file_dialog("w", "Save")
        assert result is None
        mock_gsf.assert_called_once()


def test_save_file_dialog_ctypes_returns_value(hwnd_system, no_pytron_os_system):
    # Returning True from GetSaveFileNameW makes the code reach `return buff.value`.
    # The underlying buffer starts zeroed, so buff.value == "" which is still a str.
    with patch.object(system.comdlg32, "GetSaveFileNameW", return_value=True):
        result = system.save_file_dialog("w", "Save")
        assert isinstance(result, str)


def test_save_file_dialog_default_path_and_name_combined(
    hwnd_system, no_pytron_os_system
):
    import os as _os

    with patch.object(system.comdlg32, "GetSaveFileNameW", return_value=False):
        system.save_file_dialog(
            "w", "Save", default_path="C:\\out", default_name="doc.txt"
        )
        # path joining is internal; we just verify no exception was raised


def test_save_file_dialog_rust_exception_falls_through(hwnd_system):
    mock_os = MagicMock()
    mock_os.save_file_dialog.side_effect = RuntimeError("fail")
    with patch(SYS_OS, mock_os), patch.object(
        system.comdlg32, "GetSaveFileNameW", return_value=False
    ) as mock_gsf:
        result = system.save_file_dialog("w", "Save")
        assert result is None
        mock_gsf.assert_called_once()


# ---------------------------------------------------------------------------
# system.open_folder_dialog
# ---------------------------------------------------------------------------


def test_open_folder_dialog_rust_path(hwnd_system):
    mock_os = MagicMock()
    mock_os.open_folder_dialog.return_value = "C:\\picked"
    with patch(SYS_OS, mock_os):
        result = system.open_folder_dialog("w", "Pick")
        assert result == "C:\\picked"


def test_open_folder_dialog_ctypes_returns_none_when_cancelled(
    hwnd_system, no_pytron_os_system
):
    with patch.object(system.shell32, "SHBrowseForFolderW", return_value=None):
        result = system.open_folder_dialog("w", "Pick")
        assert result is None


def test_open_folder_dialog_ctypes_returns_path_from_pidl(
    hwnd_system, no_pytron_os_system
):
    import ctypes

    fake_pidl = ctypes.c_void_p(99)

    def fake_get_path(pidl, buff):
        # buff is the actual create_unicode_buffer(260) from the production code;
        # assign via .value to avoid writing through a raw Python str pointer.
        buff.value = "C:\\folder"
        return True

    with patch.object(
        system.shell32, "SHBrowseForFolderW", return_value=fake_pidl
    ), patch.object(
        system.shell32, "SHGetPathFromIDListW", side_effect=fake_get_path
    ), patch.object(
        system.shell32, "ILFree"
    ):
        result = system.open_folder_dialog("w", "Pick")
        assert result == "C:\\folder"


def test_open_folder_dialog_ctypes_returns_none_when_path_fails(
    hwnd_system, no_pytron_os_system
):
    import ctypes

    fake_pidl = ctypes.c_void_p(99)

    with patch.object(
        system.shell32, "SHBrowseForFolderW", return_value=fake_pidl
    ), patch.object(
        system.shell32, "SHGetPathFromIDListW", return_value=False
    ), patch.object(
        system.shell32, "ILFree"
    ):
        result = system.open_folder_dialog("w", "Pick")
        assert result is None


def test_open_folder_dialog_rust_exception_falls_through(hwnd_system):
    mock_os = MagicMock()
    mock_os.open_folder_dialog.side_effect = RuntimeError("fail")
    with patch(SYS_OS, mock_os), patch.object(
        system.shell32, "SHBrowseForFolderW", return_value=None
    ):
        result = system.open_folder_dialog("w", "Pick")
        assert result is None


# ---------------------------------------------------------------------------
# system.register_protocol
# ---------------------------------------------------------------------------


def test_register_protocol_returns_false_when_no_winreg():
    with patch("pytron.platforms.windows_ops.system.winreg", None):
        assert system.register_protocol("myapp") is False


def test_register_protocol_success_mocked_winreg():
    import types

    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_winreg.CreateKey.return_value.__enter__ = MagicMock(return_value=mock_key)
    mock_winreg.CreateKey.return_value.__exit__ = MagicMock(return_value=False)
    mock_winreg.HKEY_CURRENT_USER = 0x80000001
    mock_winreg.REG_SZ = 1

    with patch("pytron.platforms.windows_ops.system.winreg", mock_winreg):
        result = system.register_protocol("myapp")
        assert result is True
        assert mock_winreg.CreateKey.call_count == 2


def test_register_protocol_returns_false_on_exception():
    mock_winreg = MagicMock()
    mock_winreg.CreateKey.side_effect = OSError("no access")

    with patch("pytron.platforms.windows_ops.system.winreg", mock_winreg):
        result = system.register_protocol("myapp")
        assert result is False


# ---------------------------------------------------------------------------
# system.set_launch_on_boot
# ---------------------------------------------------------------------------


def test_set_launch_on_boot_rust_path():
    import sys as _sys

    mock_pytron_os = MagicMock()
    mock_pytron_os.set_launch_on_boot.return_value = True
    mock_dep = MagicMock()
    mock_dep.pytron_os = mock_pytron_os

    with patch.dict(_sys.modules, {"pytron.dependencies": mock_dep}):
        result = system.set_launch_on_boot("MyApp", "C:\\app.exe", True)
    assert result is True
    mock_pytron_os.set_launch_on_boot.assert_called_with("MyApp", "C:\\app.exe", True)


def test_set_launch_on_boot_enable_via_winreg():
    import sys as _sys

    # make local import fail so winreg path is taken
    mock_dep = MagicMock()
    mock_dep.pytron_os = None  # attr available but None → AttributeError on call

    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_winreg.OpenKey.return_value.__enter__ = MagicMock(return_value=mock_key)
    mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
    mock_winreg.HKEY_CURRENT_USER = 0x80000001
    mock_winreg.KEY_SET_VALUE = 0x0002
    mock_winreg.KEY_QUERY_VALUE = 0x0001
    mock_winreg.REG_SZ = 1

    with patch.dict(_sys.modules, {"pytron.dependencies": mock_dep}), patch(
        "pytron.platforms.windows_ops.system.winreg", mock_winreg
    ):
        result = system.set_launch_on_boot("MyApp", "C:\\app.exe", enable=True)
    assert result is True
    mock_winreg.OpenKey.assert_called_once()
    mock_key.SetValueEx = MagicMock()


def test_set_launch_on_boot_disable_via_winreg():
    import sys as _sys

    mock_dep = MagicMock()
    mock_dep.pytron_os = None

    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_winreg.OpenKey.return_value.__enter__ = MagicMock(return_value=mock_key)
    mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
    mock_winreg.HKEY_CURRENT_USER = 0x80000001
    mock_winreg.KEY_SET_VALUE = 0x0002
    mock_winreg.KEY_QUERY_VALUE = 0x0001

    with patch.dict(_sys.modules, {"pytron.dependencies": mock_dep}), patch(
        "pytron.platforms.windows_ops.system.winreg", mock_winreg
    ):
        result = system.set_launch_on_boot("MyApp", "C:\\app.exe", enable=False)
    assert result is True


def test_set_launch_on_boot_disable_tolerates_file_not_found():
    import sys as _sys

    mock_dep = MagicMock()
    mock_dep.pytron_os = None

    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_key.DeleteValue.side_effect = FileNotFoundError
    mock_winreg.OpenKey.return_value.__enter__ = MagicMock(return_value=mock_key)
    mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
    mock_winreg.HKEY_CURRENT_USER = 0x80000001
    mock_winreg.KEY_SET_VALUE = 0x0002
    mock_winreg.KEY_QUERY_VALUE = 0x0001

    with patch.dict(_sys.modules, {"pytron.dependencies": mock_dep}), patch(
        "pytron.platforms.windows_ops.system.winreg", mock_winreg
    ):
        # FileNotFoundError on delete should not propagate
        result = system.set_launch_on_boot("MyApp", "C:\\app.exe", enable=False)
    assert result is True


def test_set_launch_on_boot_returns_false_when_no_winreg():
    import sys as _sys

    mock_dep = MagicMock()
    mock_dep.pytron_os = None

    with patch.dict(_sys.modules, {"pytron.dependencies": mock_dep}), patch(
        "pytron.platforms.windows_ops.system.winreg", None
    ):
        result = system.set_launch_on_boot("MyApp", "C:\\app.exe")
    assert result is False


# ---------------------------------------------------------------------------
# system.set_app_id
# ---------------------------------------------------------------------------


def test_set_app_id_rust_path():
    mock_os = MagicMock()
    with patch(SYS_OS, mock_os):
        system.set_app_id("com.example.myapp")
        mock_os.set_app_id.assert_called_with("com.example.myapp")


def test_set_app_id_ctypes_fallback():
    with patch(SYS_OS, None), patch.object(
        system.shell32, "SetCurrentProcessExplicitAppUserModelID"
    ) as mock_fn:
        system.set_app_id("com.example.myapp")
        mock_fn.assert_called_with("com.example.myapp")


def test_set_app_id_rust_exception_falls_through_to_ctypes():
    mock_os = MagicMock()
    mock_os.set_app_id.side_effect = RuntimeError("err")
    with patch(SYS_OS, mock_os), patch.object(
        system.shell32, "SetCurrentProcessExplicitAppUserModelID"
    ) as mock_fn:
        system.set_app_id("com.example.myapp")
        mock_fn.assert_called_with("com.example.myapp")


# ---------------------------------------------------------------------------
# system.set_taskbar_progress
# ---------------------------------------------------------------------------


def test_set_taskbar_progress_rust_path(hwnd_system):
    mock_os = MagicMock()
    with patch(SYS_OS, mock_os):
        system.set_taskbar_progress("w", state="normal", value=50, max_value=100)
        mock_os.set_taskbar_progress.assert_called_with(12345, "normal", 50, 100)


def test_set_taskbar_progress_noop_when_no_pytron_os(hwnd_system, no_pytron_os_system):
    # without pytron_os there is no ctypes path, just a silent return
    system.set_taskbar_progress("w", state="indeterminate", value=0)
    # no exception = pass


def test_set_taskbar_progress_silent_on_exception(hwnd_system):
    mock_os = MagicMock()
    mock_os.set_taskbar_progress.side_effect = RuntimeError("err")
    with patch(SYS_OS, mock_os):
        system.set_taskbar_progress("w", value=25)  # must not raise


def test_set_taskbar_progress_coerces_to_int(hwnd_system):
    mock_os = MagicMock()
    with patch(SYS_OS, mock_os):
        system.set_taskbar_progress("w", value=33.7, max_value=100.9)
        _, _, v, m = mock_os.set_taskbar_progress.call_args[0]
        assert isinstance(v, int)
        assert isinstance(m, int)


# ---------------------------------------------------------------------------
# system.set_clipboard_text / get_clipboard_text
# ---------------------------------------------------------------------------


def test_set_clipboard_text_rust_path():
    mock_os = MagicMock()
    mock_os.set_clipboard_text.return_value = True
    with patch(SYS_OS, mock_os):
        result = system.set_clipboard_text("hello")
        assert result is True
        mock_os.set_clipboard_text.assert_called_with("hello")


def test_set_clipboard_text_returns_false_without_pytron_os():
    with patch(SYS_OS, None):
        result = system.set_clipboard_text("hello")
        assert result is False


def test_set_clipboard_text_returns_false_on_exception():
    mock_os = MagicMock()
    mock_os.set_clipboard_text.side_effect = RuntimeError("fail")
    with patch(SYS_OS, mock_os):
        result = system.set_clipboard_text("hello")
        assert result is False


def test_get_clipboard_text_rust_path():
    mock_os = MagicMock()
    mock_os.get_clipboard_text.return_value = "world"
    with patch(SYS_OS, mock_os):
        result = system.get_clipboard_text()
        assert result == "world"


def test_get_clipboard_text_returns_none_without_pytron_os():
    with patch(SYS_OS, None):
        result = system.get_clipboard_text()
        assert result is None


def test_get_clipboard_text_returns_none_on_exception():
    mock_os = MagicMock()
    mock_os.get_clipboard_text.side_effect = RuntimeError("fail")
    with patch(SYS_OS, mock_os):
        result = system.get_clipboard_text()
        assert result is None


# ---------------------------------------------------------------------------
# system.get_system_info
# ---------------------------------------------------------------------------


def test_get_system_info_has_required_keys():
    info = system.get_system_info()
    for key in ("os", "arch", "release", "version", "cpu_count"):
        assert key in info, f"Missing key: {key}"


def test_get_system_info_cpu_count_matches_os():
    import os as _os

    info = system.get_system_info()
    assert info["cpu_count"] == _os.cpu_count()


def test_get_system_info_os_is_windows():
    info = system.get_system_info()
    assert info["os"] == "win32"


def test_get_system_info_optional_psutil_keys():
    try:
        import psutil

        info = system.get_system_info()
        assert "ram_total" in info
        assert "ram_available" in info
        assert "cpu_usage" in info
    except ImportError:
        info = system.get_system_info()
        assert "ram_total" not in info


def test_get_system_info_no_psutil():
    import sys as _sys

    # Hide psutil entirely
    with patch.dict(_sys.modules, {"psutil": None}):
        info = system.get_system_info()
    for key in ("os", "arch", "release", "version", "cpu_count"):
        assert key in info
    assert "ram_total" not in info


# ---------------------------------------------------------------------------
# system.toast
# ---------------------------------------------------------------------------


def test_toast_delegates_to_toasts_module():
    mock_config = {"title": "Hi", "message": "World"}
    with patch("pytron.platforms.windows_ops.system.toasts") as mock_toasts:
        system.toast("w", mock_config)
        mock_toasts.show_toast.assert_called_with("w", mock_config)


def test_toast_silences_exceptions():
    with patch("pytron.platforms.windows_ops.system.toasts") as mock_toasts:
        mock_toasts.show_toast.side_effect = RuntimeError("bad toast")
        # Must not propagate
        system.toast("w", {})


# ---------------------------------------------------------------------------
# window.set_utility_window
# ---------------------------------------------------------------------------


def test_set_utility_window_enable_sets_toolwindow(hwnd_window, no_pytron_os_window):
    with patch.object(
        window.user32, "GetWindowLongW", return_value=0
    ) as mock_gwl, patch.object(
        window.user32, "SetWindowLongW"
    ) as mock_swl, patch.object(
        window.user32, "SetWindowPos"
    ):
        window.set_utility_window("w", True)
        new_style = mock_swl.call_args[0][2]
        assert new_style & constants.WS_EX_TOOLWINDOW
        assert not (new_style & constants.WS_EX_APPWINDOW)


def test_set_utility_window_disable_sets_appwindow(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "GetWindowLongW", return_value=0), patch.object(
        window.user32, "SetWindowLongW"
    ) as mock_swl, patch.object(window.user32, "SetWindowPos"):
        window.set_utility_window("w", False)
        new_style = mock_swl.call_args[0][2]
        assert new_style & constants.WS_EX_APPWINDOW
        assert not (new_style & constants.WS_EX_TOOLWINDOW)


def test_set_utility_window_rust_path(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.set_utility_window("w", True)
        mock_os.set_utility_window.assert_called_with(12345, True)


def test_set_utility_window_noop_when_no_hwnd():
    with patch("pytron.platforms.windows_ops.window.get_hwnd", return_value=0), patch(
        WIN_OS, None
    ), patch.object(window.user32, "SetWindowLongW") as mock_swl:
        window.set_utility_window("w", True)
        mock_swl.assert_not_called()


def test_set_utility_window_calls_setwindowpos(hwnd_window, no_pytron_os_window):
    with patch.object(window.user32, "GetWindowLongW", return_value=0), patch.object(
        window.user32, "SetWindowLongW"
    ), patch.object(window.user32, "SetWindowPos") as mock_swp:
        window.set_utility_window("w", True)
        mock_swp.assert_called_once()
        flags = mock_swp.call_args[0][6]
        assert flags == (
            constants.SWP_NOMOVE
            | constants.SWP_NOSIZE
            | constants.SWP_NOZORDER
            | constants.SWP_FRAMECHANGED
        )


# ---------------------------------------------------------------------------
# window.set_border_color
# ---------------------------------------------------------------------------


def test_set_border_color_rust_rrggbb(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.set_border_color("w", "#FF8040")
        # #FF8040: R=0xFF G=0x80 B=0x40 → COLORREF = 0x004080FF
        mock_os.set_border_color.assert_called_with(12345, 0x004080FF)


def test_set_border_color_rust_aarrggbb(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.set_border_color("w", "#00FF8040")
        # AA=00, R=FF, G=80, B=40 → COLORREF = 0x004080FF  (same)
        mock_os.set_border_color.assert_called_with(12345, 0x004080FF)


def test_set_border_color_invalid_length_is_noop(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.set_border_color("w", "#FFF")
        mock_os.set_border_color.assert_not_called()


def test_set_border_color_ctypes_fallback_on_rust_failure(hwnd_window):
    mock_os = MagicMock()
    mock_os.set_border_color.side_effect = RuntimeError("fail")
    mock_dwmapi = MagicMock()
    import ctypes as _ct

    with patch(WIN_OS, mock_os), patch.object(_ct, "windll") as mock_wdl:
        mock_wdl.dwmapi = mock_dwmapi
        window.set_border_color("w", "#FF8040")
        mock_dwmapi.DwmSetWindowAttribute.assert_called_once()


def test_set_border_color_noop_when_no_hwnd():
    with patch("pytron.platforms.windows_ops.window.get_hwnd", return_value=0), patch(
        WIN_OS, None
    ):
        # Should not raise
        window.set_border_color("w", "#FF0000")


def test_set_border_color_rust_black(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.set_border_color("w", "#000000")
        mock_os.set_border_color.assert_called_with(12345, 0x00000000)


def test_set_border_color_rust_white(hwnd_window):
    mock_os = MagicMock()
    with patch(WIN_OS, mock_os):
        window.set_border_color("w", "#FFFFFF")
        # R=FF G=FF B=FF → 0x00FFFFFF
        mock_os.set_border_color.assert_called_with(12345, 0x00FFFFFF)
