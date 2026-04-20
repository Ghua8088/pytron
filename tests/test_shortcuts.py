"""Tests for ShortcutManager (pytron.shortcuts).

All ctypes-path tests patch `pytron.shortcuts.native_bridge` to None so the
Rust path (which calls the real blocking native bridge `get_message()`) is never
taken.  Win32 message structs are written via ctypes.memmove so that the
loop sees correct msg.message / msg.wParam values.
"""

import pytest
import sys
import threading
import ctypes
from unittest.mock import MagicMock, patch, call

# Provide stubs on non-Windows so the module can be imported
if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
if not hasattr(ctypes, "wintypes"):
    ctypes.wintypes = MagicMock()

from pytron.shortcuts import (
    ShortcutManager,
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_WIN,
    MOD_NOREPEAT,
    WM_HOTKEY,
    WM_APP_REGISTER,
    VK_MAP,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manager():
    """Create a ShortcutManager with ctypes Win32 calls pre-stubbed."""
    return ShortcutManager()


@pytest.fixture
def manager():
    mgr = _make_manager()
    yield mgr
    # Best-effort stop — never blocks because _thread_id may be None
    mgr._running = False


# ---------------------------------------------------------------------------
# _parse_combo
# ---------------------------------------------------------------------------


def test_parse_combo_ctrl_shift_a(manager):
    with patch("sys.platform", "win32"):
        mods, vk = manager._parse_combo("Ctrl+Shift+A")
    assert mods & MOD_CONTROL
    assert mods & MOD_SHIFT
    assert vk == VK_MAP["A"]
    assert mods & MOD_NOREPEAT  # always added on win32


def test_parse_combo_alt_f4(manager):
    with patch("sys.platform", "win32"):
        mods, vk = manager._parse_combo("Alt+F4")
    assert mods & MOD_ALT
    assert vk == VK_MAP["F4"]


def test_parse_combo_win_key(manager):
    with patch("sys.platform", "win32"):
        mods, vk = manager._parse_combo("Win+D")
    assert mods & MOD_WIN
    assert vk == VK_MAP["D"]


def test_parse_combo_ctrl_alias(manager):
    """CTRL and CONTROL should both map to MOD_CONTROL."""
    with patch("sys.platform", "win32"):
        mods1, _ = manager._parse_combo("Ctrl+A")
        mods2, _ = manager._parse_combo("Control+A")
    assert mods1 & MOD_CONTROL
    assert mods2 & MOD_CONTROL


def test_parse_combo_function_key(manager):
    with patch("sys.platform", "win32"):
        _, vk = manager._parse_combo("Ctrl+F12")
    assert vk == VK_MAP["F12"]


def test_parse_combo_digit(manager):
    with patch("sys.platform", "win32"):
        _, vk = manager._parse_combo("Ctrl+5")
    assert vk == VK_MAP["5"]


def test_parse_combo_space(manager):
    with patch("sys.platform", "win32"):
        _, vk = manager._parse_combo("Ctrl+Space")
    assert vk == VK_MAP["SPACE"]


def test_parse_combo_norepeat_only_on_windows(manager):
    with patch("sys.platform", "linux"):
        mods, _ = manager._parse_combo("Ctrl+A")
    assert not (mods & MOD_NOREPEAT)


# ---------------------------------------------------------------------------
# register() — high-level behaviour
# ---------------------------------------------------------------------------


def test_register_windows_starts_loop_once(manager):
    """First register() kicks off _start_message_loop; second does not."""
    with (
        patch("sys.platform", "win32"),
        patch.object(
            manager,
            "_start_message_loop",
            side_effect=lambda: setattr(manager, "_running", True),
        ) as mock_loop,
        patch.object(manager, "_queue_ready") as mock_ready,
    ):
        mock_ready.wait.return_value = True
        manager._thread_id = 1234

        manager.register("Ctrl+A", lambda: None)
        manager.register("Ctrl+B", lambda: None)

    mock_loop.assert_called_once()  # loop started exactly once


def test_register_adds_shortcut_to_dict(manager):
    with (
        patch("sys.platform", "win32"),
        patch.object(manager, "_start_message_loop"),
        patch.object(manager, "_queue_ready") as mock_ready,
    ):
        mock_ready.wait.return_value = True
        manager._thread_id = 1234

        cb = lambda: None
        manager.register("Ctrl+A", cb)

    assert 1 in manager.shortcuts
    entry = manager.shortcuts[1]
    assert entry["combo"] == "Ctrl+A"
    assert entry["callback"] is cb
    assert entry["registered"] is False


def test_register_increments_next_id(manager):
    with (
        patch("sys.platform", "win32"),
        patch.object(manager, "_start_message_loop"),
        patch.object(manager, "_queue_ready") as mock_ready,
    ):
        mock_ready.wait.return_value = True
        manager._thread_id = 1234
        manager.register("Ctrl+A", lambda: None)
        manager.register("Ctrl+B", lambda: None)

    assert 1 in manager.shortcuts
    assert 2 in manager.shortcuts


def test_register_invalid_key_does_not_add(manager):
    """A combo with an unrecognised key should be rejected."""
    with (
        patch("sys.platform", "win32"),
        patch.object(manager, "_start_message_loop"),
        patch.object(manager, "_queue_ready") as mock_ready,
    ):
        mock_ready.wait.return_value = True
        manager._thread_id = 1234
        manager.register("Ctrl+BOGUS_KEY_XYZ", lambda: None)

    assert len(manager.shortcuts) == 0


def test_register_unsupported_platform_logs_warning(manager):
    manager.logger = MagicMock()
    with patch("sys.platform", "freebsd13"):
        manager.register("Ctrl+A", lambda: None)
    manager.logger.warning.assert_called()


# ---------------------------------------------------------------------------
# _msg_loop — ctypes path (patching native_bridge=None forces it)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="ctypes Win32 only")
def test_msg_loop_registers_hotkey_on_wm_app_register(manager):
    """WM_APP_REGISTER message → RegisterHotKey called with correct args."""
    import ctypes.wintypes

    msg_tmpl = ctypes.wintypes.MSG()
    msg_tmpl.message = WM_APP_REGISTER

    call_count = [0]

    def _get_msg(lpMsg, hWnd, lo, hi):
        call_count[0] += 1
        if call_count[0] == 1:
            ctypes.memmove(lpMsg, ctypes.byref(msg_tmpl), ctypes.sizeof(msg_tmpl))
            return 1
        return 0  # causes loop to exit

    with (
        patch("pytron.shortcuts.native_bridge", None),
        patch("ctypes.windll.user32.GetMessageW", side_effect=_get_msg),
        patch("ctypes.windll.user32.RegisterHotKey", return_value=True) as mock_reg,
        patch("ctypes.windll.user32.PeekMessageW"),
        patch("ctypes.windll.user32.TranslateMessage"),
        patch("ctypes.windll.user32.DispatchMessageW"),
        patch("ctypes.windll.kernel32.GetCurrentThreadId", return_value=1234),
    ):

        manager.shortcuts[1] = {
            "id": 1,
            "fsModifiers": MOD_CONTROL,
            "vk": 0x41,
            "callback": MagicMock(),
            "registered": False,
            "combo": "Ctrl+A",
        }
        manager._running = True
        manager._msg_loop()

    mock_reg.assert_called_with(None, 1, MOD_CONTROL, 0x41)
    assert manager.shortcuts[1]["registered"] is True


@pytest.mark.skipif(sys.platform != "win32", reason="ctypes Win32 only")
def test_msg_loop_fires_callback_on_wm_hotkey(manager):
    """WM_HOTKEY message → thread spawned targeting the registered callback."""
    import ctypes.wintypes

    msg_tmpl = ctypes.wintypes.MSG()
    msg_tmpl.message = WM_HOTKEY
    msg_tmpl.wParam = 1

    call_count = [0]

    def _get_msg(lpMsg, hWnd, lo, hi):
        call_count[0] += 1
        if call_count[0] == 1:
            ctypes.memmove(lpMsg, ctypes.byref(msg_tmpl), ctypes.sizeof(msg_tmpl))
            return 1
        return 0

    cb = MagicMock()

    with (
        patch("pytron.shortcuts.native_bridge", None),
        patch("ctypes.windll.user32.GetMessageW", side_effect=_get_msg),
        patch("ctypes.windll.user32.PeekMessageW"),
        patch("ctypes.windll.user32.TranslateMessage"),
        patch("ctypes.windll.user32.DispatchMessageW"),
        patch("ctypes.windll.kernel32.GetCurrentThreadId", return_value=1234),
        patch("pytron.shortcuts.threading.Thread") as mock_thread,
    ):

        manager.shortcuts[1] = {"callback": cb}
        manager._running = True
        manager._msg_loop()

    mock_thread.assert_called_once_with(target=cb, daemon=True)
    mock_thread.return_value.start.assert_called_once()


@pytest.mark.skipif(sys.platform != "win32", reason="ctypes Win32 only")
def test_msg_loop_skips_already_registered(manager):
    """Shortcuts already marked registered must not call RegisterHotKey again."""
    import ctypes.wintypes

    msg_tmpl = ctypes.wintypes.MSG()
    msg_tmpl.message = WM_APP_REGISTER
    call_count = [0]

    def _get_msg(lpMsg, hWnd, lo, hi):
        call_count[0] += 1
        if call_count[0] == 1:
            ctypes.memmove(lpMsg, ctypes.byref(msg_tmpl), ctypes.sizeof(msg_tmpl))
            return 1
        return 0

    with (
        patch("pytron.shortcuts.native_bridge", None),
        patch("ctypes.windll.user32.GetMessageW", side_effect=_get_msg),
        patch("ctypes.windll.user32.RegisterHotKey") as mock_reg,
        patch("ctypes.windll.user32.PeekMessageW"),
        patch("ctypes.windll.user32.TranslateMessage"),
        patch("ctypes.windll.user32.DispatchMessageW"),
        patch("ctypes.windll.kernel32.GetCurrentThreadId", return_value=1234),
    ):

        manager.shortcuts[1] = {
            "id": 1,
            "fsModifiers": MOD_CONTROL,
            "vk": 0x41,
            "callback": MagicMock(),
            "registered": True,
            "combo": "Ctrl+A",
        }
        manager._running = True
        manager._msg_loop()

    mock_reg.assert_not_called()


@pytest.mark.skipif(sys.platform != "win32", reason="ctypes Win32 only")
def test_msg_loop_sets_thread_id_and_signals_ready(manager):
    """_msg_loop records thread ID and sets _queue_ready for register() to unblock."""
    with (
        patch("pytron.shortcuts.native_bridge", None),
        patch("ctypes.windll.user32.GetMessageW", return_value=0),
        patch("ctypes.windll.user32.PeekMessageW"),
        patch("ctypes.windll.user32.TranslateMessage"),
        patch("ctypes.windll.user32.DispatchMessageW"),
        patch("ctypes.windll.kernel32.GetCurrentThreadId", return_value=5678),
    ):

        manager._running = True
        manager._msg_loop()

    assert manager._thread_id == 5678
    assert manager._queue_ready.is_set()


# ---------------------------------------------------------------------------
# _msg_loop — Rust path (native_bridge present)
# ---------------------------------------------------------------------------


def test_msg_loop_rust_path_registers_hotkey():
    """With native_bridge available, the loop uses get_message / register_hotkey."""
    mock_os = MagicMock()
    mock_os.get_current_thread_id.return_value = 9999
    mock_os.init_message_queue.return_value = None
    mock_os.register_hotkey.return_value = True
    mock_os.translate_dispatch.return_value = None

    call_count = [0]

    def _get_message():
        call_count[0] += 1
        if call_count[0] == 1:
            return (WM_APP_REGISTER, 0, 0)
        return None  # WM_QUIT

    mock_os.get_message.side_effect = _get_message

    mgr = ShortcutManager()
    mgr.shortcuts[1] = {
        "id": 1,
        "fsModifiers": MOD_CONTROL,
        "vk": 0x41,
        "callback": MagicMock(),
        "registered": False,
        "combo": "Ctrl+A",
    }
    mgr._running = True

    with patch("pytron.shortcuts.native_bridge", mock_os):
        mgr._msg_loop()

    mock_os.register_hotkey.assert_called_with(0, 1, MOD_CONTROL, 0x41)
    assert mgr.shortcuts[1]["registered"] is True


def test_msg_loop_rust_path_fires_callback():
    mock_os = MagicMock()
    mock_os.get_current_thread_id.return_value = 9999
    mock_os.init_message_queue.return_value = None
    mock_os.translate_dispatch.return_value = None

    call_count = [0]

    def _get_message():
        call_count[0] += 1
        if call_count[0] == 1:
            return (WM_HOTKEY, 1, 0)
        return None

    mock_os.get_message.side_effect = _get_message

    cb = MagicMock()
    mgr = ShortcutManager()
    mgr.shortcuts[1] = {"callback": cb}
    mgr._running = True

    with (
        patch("pytron.shortcuts.native_bridge", mock_os),
        patch("pytron.shortcuts.threading.Thread") as mock_thread,
    ):
        mgr._msg_loop()

    mock_thread.assert_called_once_with(target=cb, daemon=True)
    mock_thread.return_value.start.assert_called_once()


# ---------------------------------------------------------------------------
# stop()
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PostThreadMessageW only on win32")
def test_stop_posts_wm_quit_ctypes():
    """stop() sends WM_QUIT (0x0012) to the message loop thread."""
    with (
        patch("pytron.shortcuts.native_bridge", None),
        patch("ctypes.windll.user32.PostThreadMessageW") as mock_post,
    ):
        mgr = ShortcutManager()
        mgr._running = True
        mgr._thread_id = 4321
        mgr.stop()
    mock_post.assert_called_with(4321, 0x0012, 0, 0)


def test_stop_uses_pytron_native_when_available():
    mock_os = MagicMock()
    mock_os.post_thread_message.return_value = True
    with (
        patch("pytron.shortcuts.native_bridge", mock_os),
        patch("sys.platform", "win32"),
    ):
        mgr = ShortcutManager()
        mgr._running = True
        mgr._thread_id = 4321
        mgr.stop()
    mock_os.post_thread_message.assert_called_with(4321, 0x0012, 0, 0)


def test_stop_noop_when_no_thread_id():
    """stop() must not raise when the loop was never started."""
    mgr = ShortcutManager()
    mgr.stop()  # _thread_id is None — should be a no-op
