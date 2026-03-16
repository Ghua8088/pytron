**Application (pytron.application)**

- **Purpose:** Application lifecycle manager. Bootstraps the runtime, wires together components (router, webview, plugin manager, state), and exposes the higher-level `pytron` API used by apps.

- **Key file:** `pytron/application.py`

- **Responsibilities:**
  - Initialize configuration, logging, and runtime `BuildContext` for packaging flows.
  - Discover and initialize plugins.
  - Create and configure the selected engine / webview instance.
  - Provide top-level lifecycle hooks (`start()`, `stop()`, event dispatch).

- **Runtime flow:**
  1. Parse CLI args (via `pytron.cli`) and choose an engine.
 2. Initialize `Router`, `State`, plugin system, and `Webview` instance.
 3. Start the event loop and show the main window.

- **Integration points:**
  - Calls `pytron/plugin.py` to load plugins and run `on_start`/`on_package` handlers.
  - Uses `pytron/pack` during packaging flows.

- **What to read next:** `pytron/application.py`, `pytron/cli.py`, `pytron/plugin.py`, and `docs/diagrams/app_startup.mmd`.
