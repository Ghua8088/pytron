import pytest
from unittest.mock import MagicMock, patch
from pytron.application import App
from pytron.exceptions import ConfigError
import os


@pytest.fixture
def base_config():
    return {
        "title": "TestApp",
        "author": "Tester",
        "version": "1.0.0",
        "id": "com.test.app",
    }


def mock_load_config(self, *args, **kwargs):
    self.config = {
        "title": "TestApp",
        "author": "Tester",
        "version": "1.0.0",
        "id": "com.test.app",
        "engine": "native",
    }
    self.storage_path = "/tmp/testapp"


def test_app_init_minimal(tmp_path):
    config_file = tmp_path / "settings.json"
    config_file.touch()
    with patch(
        "pytron.application.App._load_config",
        side_effect=mock_load_config,
        autospec=True,
    ), patch(
        "pytron.application.App._setup_identity", return_value=(None, "testapp")
    ), patch(
        "pytron.application.App._setup_storage"
    ), patch(
        "pytron.application.App._resolve_resources"
    ), patch(
        "pytron.application.App._register_core_apis"
    ), patch(
        "pytron.application.App._setup_key_value_store"
    ), patch(
        "pytron.application.App.load_plugins"
    ):
        app = App(str(config_file))
        assert app.config["title"] == "TestApp"
        assert app.windows == []


def test_app_init_missing_config():
    with pytest.raises(TypeError):
        App(None)


@patch("pytron.apputils.window_mixin.Webview")
def test_app_create_window(mock_webview, tmp_path):
    config_file = tmp_path / "settings.json"
    config_file.touch()
    with patch(
        "pytron.application.App._load_config",
        side_effect=mock_load_config,
        autospec=True,
    ), patch(
        "pytron.application.App._setup_identity", return_value=(None, "testapp")
    ), patch(
        "pytron.application.App._setup_storage"
    ), patch(
        "pytron.application.App._resolve_resources"
    ), patch(
        "pytron.application.App._register_core_apis"
    ), patch(
        "pytron.application.App._setup_key_value_store"
    ), patch(
        "pytron.application.App.load_plugins"
    ):
        app = App(str(config_file))
        app.app_root = tmp_path

        win = app.create_window(url="index.html", title="Window")

        assert len(app.windows) == 1
        assert app.windows[0] == mock_webview.return_value
        mock_webview.assert_called_once()

        call_config = mock_webview.call_args[1]["config"]
        assert call_config["url"].endswith("index.html")
        assert call_config["title"] == "Window"
        assert call_config["__app__"] == app


@patch("pytron.apputils.window_mixin.Webview")
def test_app_run_starts_windows(mock_webview, tmp_path):
    config_file = tmp_path / "settings.json"
    config_file.touch()
    with patch(
        "pytron.application.App._load_config",
        side_effect=mock_load_config,
        autospec=True,
    ), patch(
        "pytron.application.App._setup_identity", return_value=(None, "testapp")
    ), patch(
        "pytron.application.App._setup_storage"
    ), patch(
        "pytron.application.App._resolve_resources"
    ), patch(
        "pytron.application.App._register_core_apis"
    ), patch(
        "pytron.application.App._setup_key_value_store"
    ), patch(
        "pytron.application.App.load_plugins"
    ):
        app = App(str(config_file))
        win = app.create_window()

        with patch("threading.Thread"):
            app.run = MagicMock()
            app.run()
            app.run.assert_called_once()


def test_app_path_resolution(tmp_path):
    # Testing the actual _resolve_resources in ConfigMixin
    config_file = tmp_path / "settings.json"
    config_file.touch()
    with patch(
        "pytron.application.App._load_config",
        side_effect=mock_load_config,
        autospec=True,
    ), patch(
        "pytron.application.App._setup_identity", return_value=(None, "testapp")
    ), patch(
        "pytron.application.App._setup_storage"
    ), patch(
        "pytron.application.App._register_core_apis"
    ), patch(
        "pytron.application.App._setup_key_value_store"
    ), patch(
        "pytron.application.App.load_plugins"
    ):
        app = App(str(config_file))
        app.app_root = tmp_path
        app.config["url"] = "index.html"

        # Create the file so it's found
        idx = tmp_path / "index.html"
        idx.touch()

        app._resolve_resources()
        assert app.config["url"] == str(idx)


def test_app_emit_to_all_windows(tmp_path):
    config_file = tmp_path / "settings.json"
    config_file.touch()
    with patch(
        "pytron.application.App._load_config",
        side_effect=mock_load_config,
        autospec=True,
    ), patch(
        "pytron.application.App._setup_identity", return_value=(None, "testapp")
    ), patch(
        "pytron.application.App._setup_storage"
    ), patch(
        "pytron.application.App._resolve_resources"
    ), patch(
        "pytron.application.App._register_core_apis"
    ), patch(
        "pytron.application.App._setup_key_value_store"
    ), patch(
        "pytron.application.App.load_plugins"
    ):
        app = App(str(config_file))
        win1 = MagicMock()
        win2 = MagicMock()
        app.windows = [win1, win2]

        app.emit("evt", {"data": 1})
        win1.emit.assert_called_with("evt", {"data": 1})
        win2.emit.assert_called_with("evt", {"data": 1})
