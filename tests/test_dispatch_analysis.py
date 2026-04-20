import pytest
import asyncio
from unittest.mock import MagicMock, patch
from pytron.application import App
import os


@pytest.fixture
async def real_app(tmp_path):
    config_file = tmp_path / "settings.json"
    import json

    with open(config_file, "w") as f:
        json.dump(
            {
                "title": "TestApp",
                "id": "test.app",
                "author": "tester",
                "version": "1.0.0",
            },
            f,
        )

    with (
        patch(
            "pytron.apputils.config.ConfigComponent._setup_identity",
            return_value=(None, "testapp"),
        ),
        patch("pytron.apputils.config.ConfigComponent._setup_storage"),
        patch("pytron.apputils.config.ConfigComponent._resolve_resources"),
        patch("pytron.application.App.load_plugins"),
        patch("pytron.apputils.native.NativeComponent.set_start_on_boot"),
    ):
        app = App(str(config_file))
        # Ensure we are using the same loop as the test
        yield app


@pytest.mark.asyncio
async def test_dispatch_with_webview_fix(real_app):
    from pytron.webview import Webview

    # Create a real Webview instance with mocked native
    # We MUST patch pytron.webview.pytron_native BEFORE calling its constructor
    # To avoid opening a real window or hitting native DLLs that crash in CI.
    with patch("pytron.webview.pytron_native", MagicMock()), patch("threading.Thread"):
        win = Webview({"id": "test-win"})
        win.native = MagicMock()

        real_app.windows = [win]

        # 1. Test single dispatch
        real_app.dispatch("single", "data")
        await asyncio.sleep(0.05)

    # Webview.dispatch calls Webview.emit
    # Webview.emit calls native.eval
    win.native.eval.assert_called()
    assert "single" in win.native.eval.call_args[0][0]

    # 2. Test batched dispatch
    win.native.eval.reset_mock()
    real_app.dispatch("evt1", 1)
    real_app.dispatch("evt2", 2)
    await asyncio.sleep(0.05)

    # Should see the batch event
    win.native.eval.assert_called()
    assert "pytron:batch" in win.native.eval.call_args[0][0]
    assert (
        '[["evt1", 1], ["evt2", 2]]' in win.native.eval.call_args[0][0]
        or "evt1" in win.native.eval.call_args[0][0]
    )


@pytest.mark.asyncio
async def test_dispatch_single_bug_reproduction(real_app):
    win_no_dispatch = MagicMock(spec=["emit", "id"])
    real_app.windows = [win_no_dispatch]

    real_app.dispatch("single", "data")

    await asyncio.sleep(0.1)

    # Should fall back to emit
    win_no_dispatch.emit.assert_called_with("single", "data")
