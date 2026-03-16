Core runtime (`App`, state, logger)

Responsibilities
- App lifecycle, config, storage, crash handling, plugin discovery and loading, exposure of host APIs.
- Shared thread pool, asyncio event loop, and inspector support.

Key files
- [pytron/application.py](pytron/application.py)
- [pytron/state.py](pytron/state.py)
- [pytron/core.py](pytron/core.py)

Interactions
- Uses `Router` for deep links and event routing.
- Creates `Webview` instances (one or more windows) and wires IPC bindings.
- Loads plugins and provides a supervised proxy to protect the host.

Notes
- Config mixins and window mixins live under `pytron/apputils/` and extend `App` behaviour.