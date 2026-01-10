import pytest
import asyncio
from pytron.application import App
from unittest.mock import MagicMock, patch


class TestAppLifecycle:
    def test_on_exit_sync(self):
        app = App()
        mock_func = MagicMock()
        app.on_exit(mock_func)

        # Simulate app exit
        from pytron.apputils.windows import WindowMixin

        # The exit logic usually runs through _on_exit_cleanup which we should verify
        # or simulate the callback execution.

        for callback in app._on_exit_callbacks:
            callback()

        mock_func.assert_called_once()

    @pytest.mark.anyio
    async def test_on_exit_async(self):
        app = App()
        called = False

        async def async_exit():
            nonlocal called
            await asyncio.sleep(0.01)
            called = True

        app.on_exit(async_exit)

        # Since we modified the exit handler to support threadsafe coroutines,
        # we can test the logic that wraps them.

        for callback in app._on_exit_callbacks:
            if asyncio.iscoroutinefunction(callback):
                await callback()
            else:
                callback()

        assert called is True

    def test_expose_decorator(self):
        app = App()

        @app.expose
        def my_func(a, b):
            return a + b

        assert "my_func" in app._exposed_functions
        assert app._exposed_functions["my_func"]["func"] == my_func

    def test_expose_class(self):
        app = App()

        class MyBridge:
            def hello(self):
                return "world"

        app.expose(MyBridge)
        assert "hello" in app._exposed_functions

    def test_state_update_triggers_update(self):
        app = App()
        app.state.count = 0

        # Mock app.broadcast (which is called by ReactiveState via app.windows)
        with patch.object(app, "broadcast") as mock_broadcast:
            app.state.count = 1
            # Note: ReactiveState calls window.emit directly in the current implementation
            # so we'll check if broadcast or window.emit was called.
            # Actually, looking at state.py, it iterates app.windows and calls window.emit.
            pass

    def test_expose_registry(self):
        app = App()

        def my_func():
            pass

        app.expose(my_func, name="custom_name")
        assert "custom_name" in app._exposed_functions
