Engines — Detailed

Overview
- Location: [pytron/engines](pytron/engines)
- Purpose: Provide concrete browser/webview implementations, adapters, and forge/provision helpers for different engine backends. Engines abstract how windows are created, how IPC is marshalled, and how platform-specific engine binaries are found or provisioned.

Subfolders & key files

- chrome
  - [pytron/engines/chrome/engine.py](pytron/engines/chrome/engine.py): Chrome/Chromium-based WebView implementation (`ChromeWebView`) and `ChromeBridge` which translates Pytron native API calls into IPC messages for the shell process.
  - [pytron/engines/chrome/adapter.py](pytron/engines/chrome/adapter.py): Adapter that starts and communicates with the Chrome/Electron shell process (stdin/stdout/ipc), manages process lifecycle and raw message handling.
  - [pytron/engines/chrome/forge.py](pytron/engines/chrome/forge.py): Helper to provision or build a packaged engine (for distribution/auto-provisioning).
  - shell/: JS + packaging for the shell process (preload.js, shell.js, package.json).

- servo
  - [pytron/engines/servo/engine.py](pytron/engines/servo/engine.py): Servo-based engine implementation (`ServoWebView`) and `ServoBridge` that maps pytron calls to a Servo shell via the `ServoAdapter`.
  - [pytron/engines/servo/adapter.py](pytron/engines/servo/adapter.py): IPC adapter for Servo shell, process management and message framing.
  - [pytron/engines/servo/forge.py](pytron/engines/servo/forge.py): Provision/build helper for Servo engine and runtime assets.
  - servo/shell/: native shell sources (Rust/Cargo) used to run a standalone Servo-based process.

- native
  - [pytron/engines/native/build.py](pytron/engines/native/build.py): Build/deploy script to compile the Rust-based `pytron_native` extension and copy it into `pytron/dependencies`.
  - [pytron/engines/native/src/webview.rs](pytron/engines/native/src/webview.rs): Rust implementation of the native webview bridge (low-level event loop, IPC protocol, asset serving).
  - Cargo.toml, build scripts for building the pyo3 extension.

- misc
  - [pytron/engines/migrate.py](pytron/engines/migrate.py): Utilities for engine migration or cross-adapter compatibility.

Integration notes
- Each engine implements a bridge/adapter pattern:
  - Adapter: process-level manager (spawn, IPC channel, framing, provisioning)
  - Bridge: API shim that exposes `webview_*` functions expected by the upper `Webview` abstraction
  - WebView subclass: `ChromeWebView`, `ServoWebView`, etc. extend `Webview` and provide engine-specific behaviors.
- Engines strive to provide a unified `pytron://app/` scheme and consistent IPC semantics so `App` and `Webview` logic can be engine-agnostic.

Files to inspect for behavior
- [pytron/webview.py](pytron/webview.py) — how engines are used by core Webview
- [pytron/application.py](pytron/application.py) — engine selection and lifecycle
- Adapter files (chrome/adapter.py, servo/adapter.py) — message framing and provisioning

Common patterns
- Use of `forge.py` to auto-provision local engine binaries when not found.
- Engine selection via `PYTRON_ENGINE` or `--engine` CLI flag.
- All engines expose a `bind`/`native.bind` mechanism to register callable endpoints consumed by Rust/native layer or shell process.