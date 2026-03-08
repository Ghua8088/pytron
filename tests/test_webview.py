import pytest
import sys
import json
from unittest.mock import patch, MagicMock, ANY, PropertyMock
from pathlib import Path

# Setup global mock for module-level injection
mock_native_mod = MagicMock()
# Ensure pytron.dependencies refers to our mock so when resolve_native_module fails it hits this
sys.modules["pytron.dependencies"] = MagicMock()
sys.modules["pytron.dependencies.pytron_native"] = mock_native_mod


# Prevent threading.Thread from starting background loops
@pytest.fixture(autouse=True)
def mock_threading():
    with patch("threading.Thread") as m:
        yield m


from pytron.webview import Webview
from pytron.exceptions import NativeEngineError


@pytest.fixture(autouse=True)
def reset_mocks():
    """Resets the global mock_native_mod before each test."""
    mock_native_mod.reset_mock(side_effect=True, return_value=True)
    # Ensure NativeWebview itself returns a mock inst by default
    mock_inst = MagicMock()
    mock_native_mod.NativeWebview.return_value = mock_inst
    return mock_inst


@pytest.fixture
def webview_config():
    return {
        "url": "index.html",
        "title": "Test App",
        "dimensions": [1024, 768],
        "debug": True,
    }


def test_webview_init_error_handling(webview_config):
    # Test binary missing
    with patch("pytron.webview.pytron_native", None):
        with pytest.raises(NativeEngineError) as excinfo:
            Webview(webview_config)
        assert "binary" in str(excinfo.value)

    # Test WebView2 conflict 0x8007139F
    with patch("pytron.webview.pytron_native", mock_native_mod):
        # We patch ITSELF for minimal scope
        with patch.object(
            mock_native_mod,
            "NativeWebview",
            side_effect=RuntimeError("WebView2 error: 0x8007139F"),
        ):
            with pytest.raises(NativeEngineError) as excinfo:
                Webview(webview_config)
            assert "Conflict" in str(excinfo.value)


def test_webview_init_success(reset_mocks, webview_config):
    # reset_mocks is mock_inst = mock_native_mod.NativeWebview.return_value
    with patch("pytron.webview.pytron_native", mock_native_mod):
        wv = Webview(webview_config)
        # Check if initialized with about:blank
        mock_native_mod.NativeWebview.assert_called_with(
            webview_config["debug"],
            "about:blank",
            ANY,  # root_path
            True,  # resizable
            False,  # frameless
            None,  # store_instance
        )
        assert wv._start_url.endswith("index.html")


def test_webview_navigate(reset_mocks, webview_config):
    with patch("pytron.webview.pytron_native", mock_native_mod):
        wv = Webview(webview_config)
        wv.navigate("about:blank")
        # reset_mocks is the mock_inst that self.native points to
        reset_mocks.navigate.assert_called_once()
        args = reset_mocks.navigate.call_args[0][0]
        assert "about" in args


def test_webview_set_title(reset_mocks, webview_config):
    with patch("pytron.webview.pytron_native", mock_native_mod):
        wv = Webview(webview_config)
        wv.set_title("New Title")
        reset_mocks.set_title.assert_called_with("New Title")


def test_webview_eval(reset_mocks, webview_config):
    with patch("pytron.webview.pytron_native", mock_native_mod):
        wv = Webview(webview_config)
        wv.eval("console.log('test')")
        reset_mocks.eval.assert_called_with("console.log('test')")


def test_webview_bind(reset_mocks, webview_config):
    with patch("pytron.webview.pytron_native", mock_native_mod):
        wv = Webview(webview_config)
        mock_func = MagicMock()
        wv.bind("test_func", mock_func)
        reset_mocks.bind.assert_any_call("test_func", ANY)


def test_webview_platform_methods(reset_mocks, webview_config):
    with patch("pytron.webview.pytron_native", mock_native_mod):
        wv = Webview(webview_config)

        wv.set_fullscreen(True)
        reset_mocks.set_fullscreen.assert_called_with(True)

        wv.maximize()
        reset_mocks.maximize.assert_called_once()

        wv.minimize()
        reset_mocks.minimize.assert_called_once()

        wv.restore()
        reset_mocks.restore.assert_called_once()


def test_webview_close(reset_mocks, webview_config):
    with patch("pytron.webview.pytron_native", mock_native_mod):
        wv = Webview(webview_config)
        wv.close()
        reset_mocks.terminate.assert_called_once()


def test_webview_hide_show(reset_mocks, webview_config):
    with patch("pytron.webview.pytron_native", mock_native_mod):
        cfg = webview_config.copy()
        cfg["start_hidden"] = True
        wv = Webview(cfg)

        wv.hide()
        reset_mocks.hide.assert_called_once()
        wv.show()
        reset_mocks.show.assert_called_once()


def test_webview_windows_specific(reset_mocks, webview_config):
    with patch("pytron.webview.pytron_native", mock_native_mod), patch(
        "sys.platform", "win32"
    ), patch("pytron.platforms.windows.WindowsImplementation") as mock_win:
        cfg = webview_config.copy()
        cfg["hide_from_taskbar"] = True
        with patch.object(Webview, "hwnd", new_callable=PropertyMock) as mock_hwnd:
            mock_hwnd.return_value = 12345
            wv = Webview(cfg)
            mock_win.return_value.set_utility_window.assert_called_with(12345, True)
