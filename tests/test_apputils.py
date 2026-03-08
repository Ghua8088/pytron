import pytest
import os
import threading
import time
import sys
from unittest.mock import patch, MagicMock
from pytron.apputils.deadmansswitch import DeadMansSwitch
from pytron.apputils.shell import Shell


# DeadMansSwitch Tests
def test_deadmansswitch_init():
    mock_proc = MagicMock()
    with patch("threading.Thread") as mock_thread:
        dms = DeadMansSwitch(mock_proc)
        dms.running = False
        assert dms.proc == mock_proc
        mock_thread.assert_called_once()


@patch("os._exit")
@patch("threading.Thread")
def test_deadmansswitch_monitor_triggers(mock_thread, mock_exit):
    mock_proc = MagicMock()
    mock_proc.poll.return_value = 0
    mock_proc.pid = 1234

    dms = DeadMansSwitch(mock_proc)
    dms.running = True

    def stop_loop(*args):
        dms.running = False

    with patch("time.sleep", side_effect=stop_loop):
        dms._monitor()

    assert mock_exit.called
    assert dms.running is False


# Shell Tests
@patch("sys.platform", "win32")
@patch("os.startfile", create=True)
@patch("subprocess.run")
def test_shell_open_external_windows(mock_run, mock_startfile):
    Shell.open_external("https://google.com")
    mock_startfile.assert_called_with("https://google.com")


@patch("sys.platform", "darwin")
@patch("subprocess.run")
def test_shell_open_external_darwin(mock_run):
    with patch("shutil.which", return_value="/usr/bin/open"):
        Shell.open_external("https://google.com")
        mock_run.assert_called_with(["/usr/bin/open", "https://google.com"])


@patch("sys.platform", "linux")
@patch("subprocess.run")
def test_shell_open_external_linux(mock_run):
    with patch("shutil.which", return_value="/usr/bin/xdg-open"):
        Shell.open_external("https://google.com")
        mock_run.assert_called_with(["/usr/bin/xdg-open", "https://google.com"])


@patch("sys.platform", "win32")
@patch("subprocess.run")
def test_shell_show_item_windows(mock_run):
    with patch("shutil.which", return_value="explorer"):
        Shell.show_item_in_folder("C:\\test.txt")
        mock_run.assert_called()


def test_shell_trash_item():
    mock_s2t = MagicMock()
    with patch.dict("sys.modules", {"send2trash": MagicMock(send2trash=mock_s2t)}):
        from send2trash import send2trash

        result = Shell.trash_item("some_file.txt")
        assert result is True
        mock_s2t.assert_called_with("some_file.txt")


def test_shell_trash_item_no_lib():
    with patch.dict("sys.modules", {"send2trash": None}):
        assert Shell.trash_item("file.txt") is False
