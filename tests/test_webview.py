import pytest
import sys
from unittest.mock import patch, MagicMock, ANY, PropertyMock

from pytron.exceptions import NativeEngineError


@pytest.fixture
def mock_native():
    """
    Creates a fresh MagicMock for the native module per test, and patches
    pytron.webview.pytron_native with it. Yielding the (module_mock, instance_mock)
    tuple gives tests access to both levels.
    """
    native_mod = MagicMock()
    native_inst = MagicMock()
    native_mod.NativeWebview.return_value = native_inst

    with patch("pytron.webview.pytron_native", native_mod), patch("threading.Thread"):
        yield native_mod, native_inst


@pytest.fixture
def webview_config():
    return {
        "url": "index.html",
        "title": "Test App",
        "dimensions": [1024, 768],
        "debug": True,
        "resizable": True,
        "frameless": False,
    }


def _make_webview(config, native_mod):
    """Import inside function to avoid module-level side-effects."""
    from pytron.webview import Webview

    return Webview(config)


def test_webview_init_error_handling(webview_config):
    from pytron.webview import Webview

    # 1. Binary missing
    with patch("pytron.webview.pytron_native", None), patch("threading.Thread"):
        with pytest.raises(NativeEngineError) as exc:
            Webview(webview_config)
        assert "binary" in str(exc.value)

    # 2. WebView2 conflict 0x8007139F
    native_mod = MagicMock()
    with patch("pytron.webview.pytron_native", native_mod), patch("threading.Thread"):
        with patch.object(
            native_mod,
            "NativeWebview",
            side_effect=RuntimeError("WebView2 error: 0x8007139F"),
        ):
            with pytest.raises(NativeEngineError) as exc:
                Webview(webview_config)
            assert "Conflict" in str(exc.value)


def test_webview_init_success(mock_native, webview_config):
    from pytron.webview import Webview

    native_mod, native_inst = mock_native

    wv = Webview(webview_config)

    native_mod.NativeWebview.assert_called_with(
        webview_config["debug"],
        "about:blank",
        ANY,  # root_path
        True,  # resizable
        False,  # frameless
        None,  # store_instance
    )
    assert wv._start_url.endswith("index.html")


def test_webview_navigate(mock_native, webview_config):
    from pytron.webview import Webview

    native_mod, native_inst = mock_native

    wv = Webview(webview_config)
    wv.navigate("about:blank")

    native_inst.navigate.assert_called_once()
    assert "about" in native_inst.navigate.call_args[0][0]


def test_webview_set_title(mock_native, webview_config):
    from pytron.webview import Webview

    _, native_inst = mock_native

    wv = Webview(webview_config)
    wv.set_title("New Title")
    native_inst.set_title.assert_called_with("New Title")


def test_webview_eval(mock_native, webview_config):
    from pytron.webview import Webview

    _, native_inst = mock_native

    wv = Webview(webview_config)
    wv.eval("console.log('test')")
    native_inst.eval.assert_called_with("console.log('test')")


def test_webview_bind(mock_native, webview_config):
    from pytron.webview import Webview

    _, native_inst = mock_native

    wv = Webview(webview_config)
    wv.bind("test_func", MagicMock())
    native_inst.bind.assert_any_call("test_func", ANY)


def test_webview_platform_methods(mock_native, webview_config):
    from pytron.webview import Webview

    _, native_inst = mock_native

    wv = Webview(webview_config)

    wv.set_fullscreen(True)
    native_inst.set_fullscreen.assert_called_with(True)

    wv.maximize()
    native_inst.maximize.assert_called_once()

    wv.minimize()
    native_inst.minimize.assert_called_once()

    wv.restore()
    native_inst.restore.assert_called_once()


def test_webview_close(mock_native, webview_config):
    from pytron.webview import Webview

    _, native_inst = mock_native

    wv = Webview(webview_config)
    wv.close()
    native_inst.terminate.assert_called_once()


def test_webview_hide_show(mock_native, webview_config):
    from pytron.webview import Webview

    _, native_inst = mock_native

    cfg = {**webview_config, "start_hidden": True}
    wv = Webview(cfg)

    wv.hide()
    native_inst.hide.assert_called_once()
    wv.show()
    native_inst.show.assert_called_once()


def test_webview_windows_specific(webview_config):
    from pytron.webview import Webview

    native_mod = MagicMock()
    native_inst = MagicMock()
    native_mod.NativeWebview.return_value = native_inst

    cfg = {**webview_config, "hide_from_taskbar": True}

    with patch("pytron.webview.pytron_native", native_mod), patch(
        "threading.Thread"
    ), patch("sys.platform", "win32"), patch(
        "pytron.platforms.windows.WindowsImplementation"
    ) as mock_win, patch.object(
        Webview, "hwnd", new_callable=PropertyMock, return_value=12345
    ):
        wv = Webview(cfg)
        mock_win.return_value.set_utility_window.assert_called_with(12345, True)
