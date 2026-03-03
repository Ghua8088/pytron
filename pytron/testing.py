import asyncio
from typing import Any, Dict, List


class PytronTestClient:
    """
    A unified Headless Test runner for Pytron applications.
    Allows developers to mock the IPC pipeline and test their Python state models
    using standard `pytest` without ever booting up the Native Engine window.
    """

    def __init__(self, app, mode: str = "headless"):
        self.app = app
        self.mode = mode
        self.emitted_events: List[Dict[str, Any]] = []

        if self.mode == "headless":
            self.app.config["engine"] = "headless"

            # 1. Intercept `emit` to capture IPC events instead of routing to JavaScript
            self.original_emit = self.app.emit

            def mock_emit(event, data=None, window=None):
                self.emitted_events.append({"event": event, "data": data})

            self.app.emit = mock_emit

            # 2. Monkey-patch the blocking `run()` to instantly return in Pytest
            self._patch_app_run()

    def _patch_app_run(self):
        """Prevents `app.run()` from launching UI or blocking pytest."""

        def mock_run():
            self.app.logger.info(
                "[PytronTestClient] Intercepted app.run(). Running in headless mode."
            )
            # Simulate the application initialization flow natively
            self.app._trigger_event("ready")

        self.app.run = mock_run

    def fire_event(self, event_name: str, payload: Any = None) -> Any:
        """
        Simulates the frontend sending an IPC JavaScript payload to the Python backend.
        It directly executes the bound `@app.on` python function and returns the result.
        """
        # Search async handlers
        if event_name in self.app._events:
            # For async functions, we spin up an isolated loop so Pytest doesn't need to be async
            callback = self.app._events[event_name]
            loop = asyncio.new_event_loop()
            return loop.run_until_complete(callback(payload))

        # Search sync handlers
        elif event_name in self.app._sync_events:
            callback = self.app._sync_events[event_name]
            return callback(payload)

        else:
            raise ValueError(f"No backend function bound to event: '{event_name}'")

    def assert_emitted(self, expected_event: str) -> bool:
        """Helper for pytest to assert an IPC event was fired back to the frontend."""
        for e in self.emitted_events:
            if e["event"] == expected_event:
                return True
        raise AssertionError(
            f"IPC Event '{expected_event}' was never emitted to frontend."
        )
