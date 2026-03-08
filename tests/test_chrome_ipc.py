import pytest
import sys
import struct
import json
from unittest.mock import patch, MagicMock

from pytron.apputils.chrome_ipc import ChromeIPCServer, ChromeAdapter


@patch("sys.platform", "win32")
@patch("ctypes.windll")
def test_chrome_ipc_server_listen_windows(mock_windll):
    mock_windll.kernel32.CreateNamedPipeW.return_value = 123
    mock_windll.kernel32.ConnectNamedPipe.return_value = True

    server = ChromeIPCServer("test_pipe")
    server.listen()
    assert server.connected is True
    assert server.handle == 123


@patch("sys.platform", "linux")
@patch("socket.socket")
@patch("os.path.exists", return_value=True)
@patch("os.remove")
def test_chrome_ipc_server_listen_unix(mock_remove, mock_exists, mock_socket):
    import socket

    # Mock AF_UNIX for Windows environments where it doesn't exist
    if not hasattr(socket, "AF_UNIX"):
        socket.AF_UNIX = 1

    mock_sock_inst = MagicMock()
    mock_socket.return_value = mock_sock_inst

    mock_conn = MagicMock()
    mock_sock_inst.accept.return_value = (mock_conn, "addr")

    server = ChromeIPCServer("test_pipe")
    server.listen()

    assert server.connected is True
    assert server.sock == mock_sock_inst
    assert server.conn == mock_conn


@patch("sys.platform", "linux")
def test_chrome_ipc_server_read_loop():
    server = ChromeIPCServer("test_pipe")

    server.connected = True

    msg = {"hello": "world"}
    body = json.dumps(msg).encode("utf-8")
    header = struct.pack("<I", len(body))

    read_returns = [header, body, None]

    def mock_raw_read(n):
        if read_returns:
            return read_returns.pop(0)
        return None

    server._raw_read = mock_raw_read

    callback = MagicMock()
    server.read_loop(callback)

    assert callback.call_count == 1
    callback.assert_called_with(msg)
    assert server.connected is False


@patch("sys.platform", "linux")
@patch("threading.Thread")
@patch("subprocess.Popen")
def test_chrome_adapter_start_unix(mock_popen, mock_thread):
    adapter = ChromeAdapter(
        "/path/to/bin", {"debug": True, "frameless": True, "dimensions": [800, 600]}
    )
    adapter.start()

    mock_thread.assert_called_once()
    mock_popen.assert_called_once()

    cmd_args = mock_popen.call_args[0][0]
    assert "/path/to/bin" in cmd_args[0]
    assert any("--debug" in arg for arg in cmd_args)
    assert any("--frameless" in arg for arg in cmd_args)
    assert any("--width=800" in arg for arg in cmd_args)


def test_chrome_adapter_on_message():
    adapter = ChromeAdapter("/path/to/bin")
    callback = MagicMock()
    adapter.bind_raw(callback)

    adapter._on_message({"type": "lifecycle", "payload": "app_ready"})
    assert adapter.ready is True
    callback.assert_called_once()
