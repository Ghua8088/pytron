Webview & IPC

Responsibilities
- Host the frontend UI inside a native WebView engine.
- Provide bindings for JS -> Python RPC and binary asset serving (VAP).
- Normalize URLs to `pytron://app/` scheme for virtual root.

Key files
- [pytron/webview.py](pytron/webview.py)
- Native extension: `pytron_native` (resolved by utils)

Interactions
- Registers core bindings (pytron_*), routes calls into Python functions exposed via `App.expose()`.
- Uses underlying engines for lifecycle and rendering.

Notes
- Handles sync and async handlers, serialization via `serializer.py`, and state sync from `App.state`.