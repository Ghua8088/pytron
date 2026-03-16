Engines

Responsibilities
- Provide concrete browser/webview implementations (native pyo3 binary, Chrome/Mojo, Servo adapters).
- Offer forge/build helpers to produce engine runtimes.

Key locations
- [pytron/engines](pytron/engines)
- Native engine bindings referenced from [pytron/webview.py](pytron/webview.py)

Interactions
- Engines are chosen by `App` (env or config) and drive how webviews are created and how IPC is implemented.
- Packaging may include engine artifacts or require engine-specific packaging steps.