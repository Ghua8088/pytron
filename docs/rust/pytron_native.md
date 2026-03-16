`pytron_native` (Native webview engine, Rust)

Location
- `pytron/engines/native` (Cargo/PyO3 project). Key source: `pytron/engines/native/src/`.

Purpose
- Implement the native webview engine and IPC bridge used by the `Webview` Python class.
- Provide an embeddable `NativeWebview` Python class exposing window lifecycle, IPC binding, asset serving, and event loop integration.

Key files & responsibilities
- `src/lib.rs` — pyo3 module registration; exposes `NativeWebview`, `ChromeIPC`, and `NativeState` classes to Python.
- `src/webview.rs` — implements `NativeWebview` pyo3 class; manages creating native windows, handling webview events, registering native -> Python bindings, and providing asset serving capability used by the `pytron://` protocol.
- `src/ipc.rs` — IPC helper (`ChromeIPC`) that implements a framed, cross-platform inter-process transport (Windows named pipes, Unix domain sockets). Used by engine adapters and shell processes.
- `src/protocol.rs` — HTTP-like protocol handler for the `pytron://app/` virtual scheme. Serves files from the protocol root or in-memory served assets and injects a small JS bridge script into HTML responses so frontends can call `window.pytron.*`.
- `src/store.rs`, `src/state.rs` — persistent/native-backed state helpers used by the runtime to store and sync app state between Python and native layers.
- `src/events.rs`, `src/utils.rs` — event handling and utility functions used across the native engine.

Integration points & flow
- `pytron/webview.py` resolves the native engine by locating the `pytron.dependencies` package (a module/package containing bundled native artifacts) or other runtime locations, then instantiates `NativeWebview` when the `native` engine is selected.
- The native engine creates a real native window and registers a set of bindings (e.g., `pytron_set_title`, `pytron_serve_asset`) that the Rust layer maps to Python callbacks.
- `protocol.rs` handles requests for `pytron://app/<path>` and favors in-memory VAP assets (via `pytron_serve_asset`) before falling back to disk reads. For HTML files it injects the JS bridge to make `window.pytron` available.
- `ipc.rs` provides a robust framing protocol with a 4-byte length prefix for message boundaries and separate in/out channels; it works across named pipes (Windows) and Unix sockets.

Security & robustness
- `protocol.rs` includes path traversal mitigation and CORS handling; it injects the JS bridge only for HTML-like responses.
- IPC code carefully releases the GIL for blocking IO to avoid stalling Python threads.

When to inspect
- To alter or extend IPC framing, asset serving, or JS bridge behavior, edit `protocol.rs` and `ipc.rs`.
- To add native window features or change lifecycle semantics, inspect `webview.rs` and `events.rs`.

Build notes
- The `pytron/engines/native/build.py` script helps build/redeploy the compiled extension (copies the built artifact into `pytron/dependencies`).
- On macOS and Windows there are small platform-specific linker flags handled by `build.py` to ensure the Python extension loads correctly.