Pytron-Kit Rust dependencies (concise)

This file lists the Rust crates and key native tools used across Pytron-Kit projects (engines, platform helpers, and secure loader).

Projects scanned
- `pytron/engines/native` (pytron_native)
- `pytron/engines/servo/shell` (pytron_servo)
- `pytron/platforms/pytron_os` (pytron_os)
- `pytron/pack/secure_loader` (secure_loader)

Core Rust crates used
- pyo3 — Python bindings (PyO3) to build extension modules
- wry — WebView abstraction (used by native engine)
- tao — Windowing/event loop primitive used by wry
- serde / serde_json — Serialization
- url / urlencoding — URL handling & decoding
- mime_guess — MIME type detection for served assets
- mime, mime_guess variants used across protocol handling

Engine & windowing
- wry — high-level webview & runtime building blocks
- tao — cross-platform windowing/event-loop used by wry
- winit / surfman / softbuffer / gl — used by Servo shell for rendering
- libservo (servo) — Servo engine (git dependency)
- rustls — TLS support for Servo shell

IPC & protocol
- urlencoding — decode/encode path fragments
- mime_guess — detect content types
- byteorder — binary framing helpers (Servo shell)

Platform helpers (pytron_os)
- tray-icon — tray integration on Windows (by Tauri team)
- windows — windows-rs bindings for Win32 on Windows targets
- objc / cocoa — macOS Cocoa interop
- libc — low-level C bindings for Linux
- once_cell / dashmap — runtime utilities and concurrent maps

Secure loader & packaging
- libloading — dynamic library loading/fallbacks
- bsdiff — apply BSDIFF patches to payloads
- obfstr — string obfuscation for Windows messages
- zip — manipulate zip archives (for repacking)
- rfd — native file dialogs (used by loader for fallbacks)
- embed-resource (build-dependency) — Windows resource embedding for icon/manifest

IPC transport specifics
- On Windows: named pipes via `windows` crate wrappers
- On Unix: Unix domain sockets via std::os::unix::net
- Message framing: 4-byte little-endian length prefix implemented in `ipc.rs`/`ChromeIPC`.

External tools & toolchains (not Rust crates)
- cargo / rust toolchain — build Rust projects
- zig — used by Android builder to provide cross-cc/linking wrappers
- Android NDK — for Android cross-compiles when present
- LIEF (Python optional) — ELF/PE patching helper used by Android builder repair step

Notes
- Versions are declared in each Cargo.toml; this file provides a conceptual map rather than a pin-list. See each `Cargo.toml` for exact versions used.
- Some crates are conditional per-target (e.g., `windows` features only on Windows targets; `objc`/`cocoa` for macOS).

Where to find the Cargo.toml files
- `pytron/engines/native/Cargo.toml`
- `pytron/engines/servo/shell/Cargo.toml`
- `pytron/platforms/pytron_os/Cargo.toml`
- `pytron/pack/secure_loader/Cargo.toml`

Python dependencies

The project also depends on a set of Python packages declared in `pyproject.toml` (`[project].dependencies`) and used at runtime or during packaging. Key Python dependencies include:

- `watchfiles` — file watching utilities used by dev tools / hot reload
- `pydantic` — data validation / models
- `importlib-metadata` (for Python < 3.8) — metadata shim
- `pyinstaller` — packaging backend (optional, used by `pytron package`)
- `Pillow` — image handling
- `rich` — console rendering / pretty logs
- `nuitka` — alternative packaging backend
- `zstandard` — compression support for archives
- `comtypes` (Windows only) — COM interop on Windows
- `cryptography` — crypto primitives used for secure packaging features
- `keyring` — credential storage (plugin manager/login helpers)
- `requests` — HTTP client used by various helpers
- `Cython` — used for building C extensions / packaging workflows

Other Python tooling & optional libraries referenced in code or build helpers:

- `LIEF` (optional Python package) — used by Android `AndroidBuilder.repair_wheel` to inspect and patch binaries
- `setuptools`, `wheel` — build-system requirements (declared in `pyproject.toml` build-system.requires)
- `pytest` — testing (configured in `pytest.ini`, used in CI/tests)

Where to find Python dependency declarations
- `pyproject.toml` — primary runtime dependencies (`[project].dependencies`)
- `requirements.json` — project bootstrap / examples may reference pinned installs
- `setup.py` — packaging and package_data declarations



