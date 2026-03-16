`pytron_os` (Rust native helpers)

Location
- `pytron/platforms/pytron_os` (Cargo project exposing a Python extension via `pyo3`)

Purpose
- Provide performant, cross-platform native OS utilities that are awkward or slow to implement purely in Python (clipboard, dialogs, tray, hotkeys, message loops, window utilities).
- Expose a unified API surface to Python consumers as the `pytron_os` extension module.

Key files
- `src/lib.rs` — pyo3 module bootstrap; conditionally registers platform-specific functions into the Python module for Windows, macOS, and Linux.
- `src/win/*` — Windows-specific implementations:
  - `window.rs` — HWND helpers and window manipulation (frameless, utility window, bounds, center)
  - `dialogs.rs` — native file dialogs & message boxes
  - `tray.rs` — system tray management and popup menu handling (with fallback and a v2 tray implementation)
  - `hotkeys.rs` — global hotkey registration
  - `msgloop.rs` — message loop helpers to integrate with native event loops
  - `clipboard.rs`, `console.rs` — system clipboard and console utilities
- `src/linux/*` — Linux/GTK-specific equivalents (tray, dialogs, window, clipboard, msgloop)
- `build.py` — convenience build script to compile and copy the extension into `pytron/dependencies`.

Integration points & flow
- The Python `Webview`/platform layers import `pytron_os` (via `dependencies.py` resolution) and call into native functions for low-level OS tasks.
- `pytron_os` exposes many functions under a single module so Python code can call `pytron_os.set_taskbar_progress(...)` or `pytron_os.tray_add_icon(...)` without dealing with platform differences.

Stability & portability
- Each platform implementation attempts to fail gracefully: if a native library (e.g., GTK or Cocoa) is not available, Python code receives runtime errors or the module may warn and fallback to pure-Python implementations where possible.
- The build scripts are used by the project to produce extension artifacts (`.pyd`, `.so`, `.dylib`) and copy them into `pytron/dependencies` for runtime discovery.

When to inspect
- When adding new OS integrations (e.g., a feature requiring native APIs) or debugging window/tray behavior on a platform, inspect the matching `src/<platform>` file.
- If packaging on CI, ensure `build.py` and Cargo toolchain are configured for cross-compilation targets.