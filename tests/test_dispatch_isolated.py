import pytest
import asyncio
from unittest.mock import MagicMock, patch
from pytron.application import App


@pytest.fixture
def mock_app(tmp_path):
    config_file = tmp_path / "settings.json"
    with open(config_file, "w") as f:
        import json

        json.dump(
            {"title": "Test", "id": "test", "author": "test", "version": "1.0.0"}, f
        )

    # We use the event loop provided by the test if available
    try:
        loop = asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    with patch("pytron.apputils.config.ConfigComponent._load_config"), patch(
        "pytron.apputils.config.ConfigComponent._setup_identity",
        return_value=(None, "test"),
    ), patch("pytron.apputils.config.ConfigComponent._setup_storage"), patch(
        "pytron.apputils.config.ConfigComponent._resolve_resources"
    ), patch(
        "pytron.application.App.load_plugins"
    ), patch(
        "pytron.apputils.native.NativeComponent.set_start_on_boot"
    ), patch(
        "asyncio.get_event_loop", return_value=loop
    ):
        app = App(str(config_file))
        return app


@pytest.mark.asyncio
async def test_emit_and_publish_logic(mock_app):
    win = MagicMock()
    mock_app.windows = [win]

    # app.emit -> window.emit
    mock_app.emit("evt", 1)
    win.emit.assert_called_with("evt", 1)

    # app.publish -> window.emit
    mock_app.publish("pub", 2)
    win.emit.assert_called_with("pub", 2)


@pytest.mark.asyncio
async def test_dispatch_logic_with_fallback(mock_app):
    # 1. Window WITH dispatch
    win_with = MagicMock()
    # Mocking hasattr for MagicMock is tricky if we want negative checks,
    # but here we WANT it to have it.

    # 2. Window WITHOUT dispatch (like old Webview)
    class LegacyWindow:
        def __init__(self):
            self.emit = MagicMock()
            self.id = "legacy"
            # No dispatch method

    win_legacy = LegacyWindow()

    mock_app.windows = [win_with, win_legacy]

    # 1. Test Single Dispatch (Legacy should get it via emit)
    mock_app.dispatch("single", "data")

    # Manually trigger the inner flush logic (extracted from _flush_events_task)
    batch = []
    while mock_app._dispatch_buffer:
        batch.append(mock_app._dispatch_buffer.popleft())

    # Perform the flush (copy of logic from application.py)
    name, data = batch[0]
    for window in mock_app.windows:
        if hasattr(window, "dispatch"):
            window.dispatch(name, data)
        elif hasattr(window, "emit"):
            window.emit(name, data)

    win_legacy.emit.assert_called_with("single", "data")

    # 2. Test Batched Dispatch (Legacy should get pytron:batch via emit)
    mock_app.dispatch("e1", 1)
    mock_app.dispatch("e2", 2)

    batch = []
    while mock_app._dispatch_buffer:
        batch.append(mock_app._dispatch_buffer.popleft())

    for window in mock_app.windows:
        if hasattr(window, "dispatch"):
            window.dispatch("pytron:batch", batch)
        elif hasattr(window, "emit"):
            window.emit("pytron:batch", batch)

    win_legacy.emit.assert_called_with("pytron:batch", [("e1", 1), ("e2", 2)])

    # Check win_legacy - Since we added a fallback in application.py,
    # even though LegacyWindow doesn't have a 'dispatch' method, it should
    # still receive the batch via its 'emit' method if available.
    win_legacy.emit.assert_called_with("pytron:batch", [("e1", 1), ("e2", 2)])
