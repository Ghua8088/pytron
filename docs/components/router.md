**Router**

- **Purpose:** Resolve deep links and internal routes (e.g., `pytron://...`) to application handlers. Centralized place for mapping URL-like paths to Python callbacks or UI views.

- **Key file:** `pytron/router.py`

- **Responsibilities:**
  - Parse route strings and extract parameters.
  - Register route handlers and dispatch incoming navigation/deep-link events.
  - Provide utilities for generating internal URLs used by the webview JS bridge.

- **Typical flow:**
  1. App or JS triggers navigation to a `pytron://` URL.
 2. Router parses URL and finds the best matching handler.
 3. Router invokes the Python callback or publishes an event on the app event bus.

- **Integration points:**
  - `pytron.application` registers default routes on startup.
  - `pytron.webview` and native protocol handlers call into the Router for `pytron://` requests.

- **What to read next:** `pytron/router.py`, `pytron/webview.py`, and `docs/diagrams/app_startup.mmd`.
