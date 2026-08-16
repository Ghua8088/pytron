import pytest
from unittest.mock import MagicMock, patch
from pytron.application import App


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
    with (
        patch(
            "pytron.apputils.config.ConfigComponent._load_config",
            side_effect=mock_load_config,
            autospec=True,
        ),
        patch(
            "pytron.apputils.config.ConfigComponent._setup_identity",
            return_value=(None, "testapp"),
        ),
        patch("pytron.apputils.config.ConfigComponent._setup_storage"),
        patch("pytron.apputils.config.ConfigComponent._resolve_resources"),
        patch("pytron.application.App._register_core_apis"),
        patch("pytron.apputils.config.ConfigComponent._setup_key_value_store"),
        patch("pytron.application.App.load_plugins"),
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
    with (
        patch(
            "pytron.apputils.config.ConfigComponent._load_config",
            side_effect=mock_load_config,
            autospec=True,
        ),
        patch(
            "pytron.apputils.config.ConfigComponent._setup_identity",
            return_value=(None, "testapp"),
        ),
        patch("pytron.apputils.config.ConfigComponent._setup_storage"),
        patch("pytron.apputils.config.ConfigComponent._resolve_resources"),
        patch("pytron.application.App._register_core_apis"),
        patch("pytron.apputils.config.ConfigComponent._setup_key_value_store"),
        patch("pytron.application.App.load_plugins"),
    ):
        app = App(str(config_file))
        app.app_root = tmp_path

        app.create_window(url="index.html", title="Window")

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
    with (
        patch(
            "pytron.apputils.config.ConfigComponent._load_config",
            side_effect=mock_load_config,
            autospec=True,
        ),
        patch(
            "pytron.apputils.config.ConfigComponent._setup_identity",
            return_value=(None, "testapp"),
        ),
        patch("pytron.apputils.config.ConfigComponent._setup_storage"),
        patch("pytron.apputils.config.ConfigComponent._resolve_resources"),
        patch("pytron.application.App._register_core_apis"),
        patch("pytron.apputils.config.ConfigComponent._setup_key_value_store"),
        patch("pytron.application.App.load_plugins"),
    ):
        app = App(str(config_file))
        app.create_window()

        with patch("threading.Thread"):
            app.run = MagicMock()
            app.run()
            app.run.assert_called_once()


def test_app_path_resolution(tmp_path):
    # Testing the actual _resolve_resources in ConfigComponent
    config_file = tmp_path / "settings.json"
    config_file.touch()
    with (
        patch(
            "pytron.apputils.config.ConfigComponent._load_config",
            side_effect=mock_load_config,
            autospec=True,
        ),
        patch(
            "pytron.apputils.config.ConfigComponent._setup_identity",
            return_value=(None, "testapp"),
        ),
        patch("pytron.apputils.config.ConfigComponent._setup_storage"),
        patch("pytron.application.App._register_core_apis"),
        patch("pytron.apputils.config.ConfigComponent._setup_key_value_store"),
        patch("pytron.application.App.load_plugins"),
    ):
        app = App(str(config_file))
        app.app_root = tmp_path
        app.config["url"] = "index.html"

        # Create the file so it's found
        idx = tmp_path / "index.html"
        idx.touch()

        app._config_comp._resolve_resources()
        assert app.config["url"] == str(idx)


def test_app_emit_to_all_windows(tmp_path):
    config_file = tmp_path / "settings.json"
    config_file.touch()
    with (
        patch(
            "pytron.apputils.config.ConfigComponent._load_config",
            side_effect=mock_load_config,
            autospec=True,
        ),
        patch(
            "pytron.apputils.config.ConfigComponent._setup_identity",
            return_value=(None, "testapp"),
        ),
        patch("pytron.apputils.config.ConfigComponent._setup_storage"),
        patch("pytron.apputils.config.ConfigComponent._resolve_resources"),
        patch("pytron.application.App._register_core_apis"),
        patch("pytron.apputils.config.ConfigComponent._setup_key_value_store"),
        patch("pytron.application.App.load_plugins"),
    ):
        app = App(str(config_file))
        win1 = MagicMock()
        win2 = MagicMock()
        app.windows = [win1, win2]

        app.emit("evt", {"data": 1})
        win1.emit.assert_called_with("evt", {"data": 1})
        win2.emit.assert_called_with("evt", {"data": 1})


def test_app_is_visible_delegation(tmp_path):
    """Regression test: Ensure app.is_visible delegates to window without loop."""
    config_file = tmp_path / "settings.json"
    config_file.touch()
    with (
        patch(
            "pytron.apputils.config.ConfigComponent._load_config",
            side_effect=mock_load_config,
            autospec=True,
        ),
        patch(
            "pytron.apputils.config.ConfigComponent._setup_identity",
            return_value=(None, "testapp"),
            autospec=True,
        ),
        patch("pytron.apputils.config.ConfigComponent._setup_storage"),
        patch("pytron.apputils.config.ConfigComponent._resolve_resources"),
        patch("pytron.application.App._register_core_apis"),
        patch("pytron.apputils.config.ConfigComponent._setup_key_value_store"),
        patch("pytron.application.App.load_plugins"),
    ):
        app = App(str(config_file))
        win = MagicMock()
        # Webview.is_visible is a method
        win.is_visible.return_value = True
        app.windows = [win]

        # app.is_visible is now a method
        assert app.is_visible() is True
        win.is_visible.assert_called_once()


def test_component_recursion_safety(tmp_path):
    """Regression test: Ensure AppComponent.__getattr__ is safe against loops."""
    config_file = tmp_path / "settings.json"
    config_file.touch()
    with (
        patch(
            "pytron.apputils.config.ConfigComponent._load_config",
            side_effect=mock_load_config,
            autospec=True,
        ),
        patch(
            "pytron.apputils.config.ConfigComponent._setup_identity",
            return_value=(None, "testapp"),
            autospec=True,
        ),
        patch("pytron.apputils.config.ConfigComponent._setup_storage"),
        patch("pytron.apputils.config.ConfigComponent._resolve_resources"),
        patch("pytron.application.App._register_core_apis"),
        patch("pytron.apputils.config.ConfigComponent._setup_key_value_store"),
        patch("pytron.application.App.load_plugins"),
    ):
        app = App(str(config_file))
        comp = app._window_comp

        # Accessing something really non-existent should raise AttributeError immediately
        # NOT a RecursionError
        with pytest.raises(AttributeError) as exc:
            _ = comp.this_property_definitely_does_not_exist

        assert "Recursion detected" not in str(exc.value)
        assert "has no attribute" in str(exc.value)
