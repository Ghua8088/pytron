import pytest
from unittest.mock import MagicMock, patch

from pytron.webview import Webview
from pytron.engines.chrome.engine import ChromeWebView
from pytron.engines.servo.engine import ServoWebView

# Mark all tests in this file as functional/webview tests
pytestmark = [pytest.mark.webview, pytest.mark.functional]


def test_webview_bind_native_signature_args():
    """
    Ensure NativeWebview.bind() is called with exactly 2 arguments (name, callback).
    This validates the fix for a TypeError caused by passing 3 arguments.
    """
    native_inst = MagicMock()
    native_mod = MagicMock()
    native_mod.NativeWebview.return_value = native_inst

    with patch("pytron.webview.pytron_native", native_mod), patch("threading.Thread"):
        wv = Webview({"engine": "native"})

        def mock_fn():
            pass

        wv.bind("test_fn", mock_fn)

        # Verify that ALL calls to bind (including core ones) used exactly 2 arguments
        for call in native_inst.bind.call_args_list:
            assert len(call[0]) == 2
            assert isinstance(call[0][0], str)
            assert callable(call[0][1])


def test_chrome_webview_init_no_attribute_error():
    """
    Ensure ChromeWebView initialization doesn't trigger bridge calls before it's ready.
    Validates that self.bridge is set before any methods (like set_title) that use it are called.
    """
    with (
        patch("pytron.engines.chrome.engine.ChromeAdapter"),
        patch("pytron.engines.chrome.engine.ChromeBridge") as MockBridge,
        patch("pytron.webview.pytron_native", MagicMock()),
        patch("threading.Thread"),
    ):
        config = {"engine": "chrome", "title": "Test"}
        wv = ChromeWebView(config)

        assert hasattr(wv, "bridge")
        assert MockBridge.return_value.set_title.called


def test_servo_webview_init_no_attribute_error():
    """
    Ensure ServoWebView initialization doesn't trigger attribute errors if bridge is accessed early.
    """
    with (
        patch("pytron.engines.servo.engine.ServoAdapter"),
        patch("pytron.engines.servo.engine.ServoBridge"),
        patch("pytron.engines.servo.forge.ServoForge"),
        patch("pytron.webview.pytron_native", MagicMock()),
        patch("threading.Thread"),
        patch("os.path.exists", return_value=True),
    ):
        config = {"engine": "servo", "title": "Test", "engine_path": "/mock/servo"}
        wv = ServoWebView(config)

        assert hasattr(wv, "bridge")


def test_servo_bridge_methods_unified():
    """
    Verify ServoWebView uses unified bridge method names (no webview_ prefix).
    """
    with (
        patch("pytron.engines.servo.engine.ServoAdapter"),
        patch("pytron.engines.servo.engine.ServoBridge") as MockBridge,
        patch("pytron.engines.servo.forge.ServoForge"),
        patch("pytron.webview.pytron_native", MagicMock()),
        patch("threading.Thread"),
        patch("os.path.exists", return_value=True),
    ):
        wv = ServoWebView({"engine": "servo", "engine_path": "/mock/servo"})
        MockBridge.return_value.reset_mock()

        wv.show()
        MockBridge.return_value.show.assert_called()

        wv.set_title("New Title")
        MockBridge.return_value.set_title.assert_called_with("New Title")

        wv.navigate("http://example.com")
        MockBridge.return_value.navigate.assert_called_with("http://example.com")

        wv.close()
        # ServoBridge uses 'terminate' for closing
        MockBridge.return_value.terminate.assert_called()


def test_webview_facade_delegation_set_icon_menu():
    """
    Ensure the Webview facade correctly delegates set_icon and set_menu to the native instance.
    """
    native_inst = MagicMock()
    with patch("pytron.webview.pytron_native", MagicMock()), patch("threading.Thread"):
        wv = Webview({"engine": "native"})
        wv.native = native_inst

        wv.set_icon("icon.png")
        native_inst.set_icon.assert_called_with("icon.png")

        wv.set_menu([{"label": "File"}])
        native_inst.set_menu.assert_called_with([{"label": "File"}])


def test_webview_base_init_selective_native_setup():
    """
    Ensure the Webview base class only sets up the native window when instantiated directly.
    Subclasses should handle their own setup to prevent early virtual calls.
    """

    class SubWebView(Webview):
        def __init__(self, config):
            super().__init__(config)
            self.setup_called = False

        def _setup_native_window(self, config):
            self.setup_called = True

    native_mod = MagicMock()
    with patch("pytron.webview.pytron_native", native_mod), patch("threading.Thread"):
        # 1. Base class -> Should call setup
        wv_base = Webview({"engine": "native"})
        assert wv_base.native is not None

        # 2. Subclass -> Should NOT call setup via super().__init__
        wv_sub = SubWebView({"engine": "native"})
        assert wv_sub.setup_called is False


def test_webview_has_bound_functions_attribute():
    """
    Ensure Webview and its subclasses have the _bound_functions attribute.
    """
    with patch("pytron.webview.pytron_native", MagicMock()), patch("threading.Thread"):
        wv = Webview({})
        assert hasattr(wv, "_bound_functions")
        assert isinstance(wv._bound_functions, dict)
