import pytest
import sys
import json
import io
import os
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from pytron.updater import Updater
from pytron.exceptions import UpdateError


@pytest.fixture
def updater():
    return Updater(current_version="1.0.0")


def test_updater_init():
    upd = Updater(current_version="1.2.3")
    assert upd.current_version == "1.2.3"


def test_updater_check_available(updater):
    # We must patch sys.frozen = True for check to run
    with patch("sys.frozen", True, create=True):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"version": "1.1.0", "url": "http://e.com/upd"}
        ).encode()
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            res = updater.check("https://update.pytron.org/check")
            assert res["version"] == "1.1.0"


def test_updater_check_up_to_date(updater):
    with patch("sys.frozen", True, create=True):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"version": "1.0.0"}).encode()
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            res = updater.check("https://update.pytron.org/check")
            assert res is None


def test_updater_check_error(updater):
    with patch("sys.frozen", True, create=True):
        with patch("urllib.request.urlopen", side_effect=Exception("Network Down")):
            with pytest.raises(UpdateError):
                updater.check("https://update.pytron.org/check")


def test_updater_download_patch(updater):
    with patch("sys.frozen", True, create=True):
        with patch("sys.executable", "C:\\app\\app.exe"):
            with patch("pathlib.Path.exists", return_value=True):  # For is_secure check
                update_info = {"version": "1.1.0", "patch_url": "http://e.com/patch"}

                with patch("urllib.request.urlretrieve") as mock_retrieve:
                    with patch("sys.exit") as mock_exit:
                        with patch("subprocess.Popen"):
                            updater.download_and_install(update_info)
                            mock_retrieve.assert_called()
                            mock_exit.assert_called_with(0)


def test_updater_download_full(updater):
    with patch("sys.frozen", True, create=True):
        with patch("sys.executable", "C:\\app\\app.exe"):
            # Path.exists returns False for is_secure to trigger full download
            with patch("pathlib.Path.exists", return_value=False):
                update_info = {
                    "version": "1.1.0",
                    "url": "http://e.com/installer.exe",
                    "hash": "abc",
                }

                with patch("urllib.request.urlretrieve"):
                    # Patch hashlib inside pytron.updater (local import inside method)
                    with patch("pytron.updater.hashlib") as mock_hashlib:
                        mock_sha = MagicMock()
                        mock_sha.hexdigest.return_value = "abc"
                        mock_hashlib.sha256.return_value = mock_sha

                        # mock_open: first read returns data, second returns b"" to end loop
                        m = mock_open(read_data=b"file content")
                        m.return_value.read.side_effect = [b"file content", b""]
                        with patch("builtins.open", m):
                            # Patch subprocess and os inside updater so platform-specific
                            # code (chmod on Linux, creationflags on Windows) never touches
                            # the real filesystem.
                            with patch("pytron.updater.subprocess"), patch("os.chmod"):
                                with patch("sys.exit") as mock_exit:
                                    updater.download_and_install(update_info)
                                    mock_exit.assert_called_with(0)
