Platforms — Detailed

Overview
- Location: [pytron/platforms](pytron/platforms)
- Purpose: OS-specific helpers and shims that expose native capabilities (dialogs, tray, window management, taskbar progress, protocol registration) to the `App` and `Webview` layers. Platform modules centralize per-OS behavior so higher layers stay portable.

Top-level modules
- [pytron/platforms/__init__.py](pytron/platforms/__init__.py) — platform resolver (empty placeholder present). Use platform-specific `WindowsImplementation`, `DarwinImplementation`, `LinuxImplementation`.
- [pytron/platforms/interface.py] (platforms/interface.py) — defines `PlatformInterface` (abstract contract used by implementations).

Per-OS implementations & subfolders

- Windows
  - [pytron/platforms/windows.py](pytron/platforms/windows.py): `WindowsImplementation` adapter that calls into `windows_ops` helpers.
  - [pytron/platforms/windows_ops/window.py](pytron/platforms/windows_ops/window.py): Window creation and HWND helpers.
  - [pytron/platforms/windows_ops/webview.py](pytron/platforms/windows_ops/webview.py): Windows-specific webview utilities (mostly deprecated/compat shims).
  - [pytron/platforms/windows_ops/system.py](pytron/platforms/windows_ops/system.py): System dialogs, toasts, taskbar progress, app-id, registry operations.
  - [pytron/platforms/windows_ops/toasts.py], utils, constants: helper utilities for WinRT/COM bindings.

- macOS (Darwin)
  - [pytron/platforms/darwin.py](pytron/platforms/darwin.py): `DarwinImplementation` delegating to `darwin_ops`.
  - [pytron/platforms/darwin_ops/window.py](pytron/platforms/darwin_ops/window.py): Cocoa/NSWindow wrappers.
  - [pytron/platforms/darwin_ops/webview.py](pytron/platforms/darwin_ops/webview.py): WebView/Cocoa integration shims.
  - [pytron/platforms/darwin_ops/system.py], libs.py: ObjC bridging and library loaders.

- Linux
  - [pytron/platforms/linux.py](pytron/platforms/linux.py): `LinuxImplementation` delegating to `linux_ops`.
  - [pytron/platforms/linux_ops/window.py](pytron/platforms/linux_ops/window.py): GTK/GObject window logic.
  - [pytron/platforms/linux_ops/webview.py](pytron/platforms/linux_ops/webview.py): WebKit/GTK integration.
  - [pytron/platforms/linux_ops/system.py], libs.py: GTK detection and native library helpers.

- Android
  - [pytron/platforms/android/android.py](pytron/platforms/android/android.py): Android runtime integration and high-level API.
  - [pytron/platforms/android/builder.py](pytron/platforms/android/builder.py): Build orchestration for Android targets (cross-compilation, wheel repair, Zig/NDK handling). Critical for packaging to Android.
  - [pytron/platforms/android/ops/*](pytron/platforms/android/ops): CLI operations (`init`, `build`, `run`, `logcat`, etc.) that call into `AndroidBuilder` and project scaffolding.
  - shell assets: Android app shell templates and native integration points (assets/python/main.py).

- pytron_os / native helpers
  - [pytron/platforms/pytron_os] (folder): Rust or native OS helper library used by platform features (e.g., toggle_maximize, window visibility). Some OS operations are implemented in compiled modules and surfaced via `dependencies.py`.

Patterns & responsibilities
- Each OS implementation provides the contract defined by `PlatformInterface` and delegates to a small set of `*_ops` modules for low-level implementation.
- `Webview` and `App` use `PlatformImplementation` instances to call OS functions; platform modules attempt to fail gracefully when native libs are absent and emit warnings (e.g., GTK/ObjC not found).
- Android builder includes heavy cross-compilation logic (zig toolchain, NDK fallback, wheel renaming and ELF patching) — this is a critical packaging path and should be audited if deploying to Android.

Files to inspect for behavior
- [pytron/webview.py](pytron/webview.py) — where platform helpers are consumed
- [pytron/application.py](pytron/application.py) — plugin discovery and platform-dependent identity/single-instance logic
- Windows/darwin/linux ops files — for dialog/tray/taskbar specifics

Next actions
- I can expand any platform `*_ops` file into a short summary of exported functions and major control flows.
- I can also generate a per-platform sequence diagram (startup, show window, dialogs) if useful.