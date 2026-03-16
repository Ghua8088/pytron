**Workflows — Pytron-Kit**

This document summarizes the common developer and release workflows used in Pytron-Kit: how to run during development, package apps, build native engines and helpers, produce Android builds, work with plugins, and run tests/CI.

**Run (Development)**
- **Purpose**: Run an app locally with hot-reload and dev conveniences.
- **Entry**: `pytron/cli.py` -> `pytron run`
- **Typical command**:

```bash
pytron run path/to/app.py --dev
```

- **Behavior**:
  - Starts the `App` lifecycle (`pytron/application.py`).
  - Chooses engine via `PYTRON_ENGINE` or `--engine` / `--chrome` flags.
  - Creates `Webview` instances (native, chrome, servo) which load your frontend URL.
  - Watches files (via `watchfiles`) and can trigger frontend rebuilds/hot reload.

**Frontend build (JS)**
- **Purpose**: Build frontend assets (React/Vite/etc.) used by the webview.
- **Entry**: `pytron/commands/build.py` (proxied by `pytron cli frontend`)
- **Typical command**:

```bash
pytron frontend --provider npm build
```

- **Behavior**: Runs the provider (`npm`, `yarn`, `pnpm`, `bun`) in the `frontend` folder; built assets are referenced by `Webview` via the `pytron://app/` virtual root.

**Package (Desktop release)**
- **Purpose**: Produce a distributable executable (PyInstaller/Nuitka) and optional installers.
- **Entry**: `pytron package` (see `pytron/commands/package.py`)
- **Typical command**:

```bash
pytron package app.py --name MyApp --icon path/to/icon.ico --installer
```

- **Behavior**:
  - Runs the `pack` pipeline (`pytron/pack/pipeline.py`) which composes `BuildModule`s for asset collection, hooks, wrappers, and post-processing.
  - Supports multiple backends: PyInstaller (default), Nuitka (optional), and Rust-based secure loader integration.
  - Plugins can contribute via `Plugin.invoke_package_hook(context)`.
  - Optionally builds NSIS installer using resources in `pytron/installer`.

**Secure packaging (Rust bootloader / fortress)**
- **Purpose**: Hardened packaging that embeds a Rust `secure_loader` to isolate and protect Python payloads.
- **Files**: `pytron/pack/secure_loader/*` (Rust project)
- **Behavior**:
  - `secure_loader` builds a static/native binary that sets up a locked Python environment, runs anti-debug checks, and loads the packaged `app` module.
  - Packaging pipeline places `_internal`, `app.bundle`, and `secure_loader` together for distribution.

**Build native engine (`pytron_native`)**
- **Purpose**: Build the native webview engine (Rust/PyO3) used by `Webview` for native rendering and IPC.
- **Files**: `pytron/engines/native/` (`build.py`, `Cargo.toml`, `src/`)
- **Typical command** (from repo root):

```bash
python pytron/engines/native/build.py
# or from engines/native: cargo build --release
```

- **Behavior**: Compiles Rust crate, copies built artifact into `pytron/dependencies` for runtime discovery; pay attention to platform-specific linker flags in `build.py`.

**Build `pytron_os` (native platform helpers)**
- **Purpose**: Produce the `pytron_os` Python extension exposing native OS APIs (tray, dialogs, clipboard, hotkeys).
- **Files**: `pytron/platforms/pytron_os/` (Cargo.toml, src/)
- **Typical command**:

```bash
python pytron/platforms/pytron_os/build.py
# or: cargo build --release (then copy artifact to pytron/dependencies)
```

- **Behavior**: Builds conditional implementations for Windows/macOS/Linux and copies the extension into `pytron/dependencies` so Python code can import native helpers.

**Engine provisioning (Chrome / Servo)**
- **Purpose**: Auto-provision engine shells (Electron/Chrome-based shell or Servo shell) when not bundled.
- **Files**: `pytron/engines/chrome/forge.py`, `pytron/engines/servo/forge.py`
- **Behavior**: `Forge` helpers download or build the required engine binary and place it under `~/.pytron/engines` or `pytron/dependencies` for local discovery. Engines are then launched by adapters (`adapter.py`) which manage IPC/process lifecycle.

**Android build & packaging**
- **Purpose**: Cross-compile Python dependencies and bundle a minimal Android shell (AAB/APK).
- **Files**: `pytron/platforms/android/builder.py`, `pytron/platforms/android/ops/*`, Android shell templates under `platforms/android/shell`.
- **Typical flow**:
  - `pytron android init` — scaffold Android project.
  - `pytron android build` — run the `AndroidBuilder` flow which:
    - Attempts to download prebuilt wheels for Android ABI or uses Zig+NDK to cross-compile native extensions.
    - Repairs wheels (LIEF optional) and flattens native libs.
    - Generates `_sysconfigdata__linux_*` spoof and meson cross files for building wheels.
  - Outputs APK/AAB in `platforms/android/shell/app/build/outputs`.

**Plugin development & installation**
- **Purpose**: Extend runtime via plugins (Python + optional JS UI).
- **Files**: `pytron/plugin.py`, plugin folders with `manifest.json` and `entry_point`.
- **Commands**:

```bash
pytron plugin create my-plugin
pytron plugin install username.repo
pytron plugin list
pytron plugin uninstall my-plugin
```

- **Behavior**:
  - Plugins declare manifest fields (`name`, `version`, `entry_point`, `python_dependencies`, `npm_dependencies`).
  - `App` discovers plugins in `plugins/` or configured `plugins_dir` and loads them into a supervised context (`SupervisedApp`).
  - Plugins may be loaded isolated (thread) or in-process and can register package hooks (`on_package`).

**Installing plugin dependencies**
- `Plugin.install_dependencies()` will try to install Python deps via `pip` (respecting a local venv if present) and JS deps via the chosen provider inside the plugin folder.
- In packaged/frozen apps, plugin dependency installation is skipped.

**Testing & CI**
- **Tests**: `pytest` configured in `pytest.ini`; run with:

```bash
pytest
```

- **Unit tests**: Engine-specific and platform-specific tests exist under `tests/` (e.g., `test_engine.py`, `test_platform_ops.py`).
- **CI notes**: Ensure native crates are built or mock `pytron_native`/`pytron_os` in CI, or run tests with pure-Python fallbacks when native libs are unavailable.

**Local development tips**
- Keep `pytron/dependencies` populated with built native artifacts for fastest iteration (copy `.pyd`/`.so` after building Rust projects).
- Use `--engine` or `PYTRON_ENGINE` env var to switch engines quickly.
- Use `pytron run --dev` for hot reload; ensure frontend `provider` is running if using a dev server.

**Release / Publishing**
- Typical release builds:
  1. Build `pytron_native` and `pytron_os` for target platforms and copy artifacts into `pytron/dependencies`.
  2. Run `pytron package` with `--one-file`/`--one-dir` and `--installer` flags as needed.
  3. Optionally sign installers and create update metadata (used by `pytron/updater.py`).

**Troubleshooting pointers**
- Native import errors: verify compiled artifacts exist in `pytron/dependencies` and match Python ABI (see `pytron/engines/native/build.py` flags).
- Webview loading errors: check `protocol.rs` injection logic and asset existence under the resolved root path.
- Android build failures: check `Zig` availability and NDK; inspect `AndroidBuilder._ensure_zig` and `_find_ndk_info` for env expectations.

**Files of interest per workflow**
- Run / Dev: `pytron/cli.py`, `pytron/application.py`, `pytron/webview.py`
- Package: `pytron/pack/pipeline.py`, `pytron/pack/*` modules, `pytron/plugin.py`
- Secure loader: `pytron/pack/secure_loader/*`
- Native engine: `pytron/engines/native/*` and `pytron/engines/native/build.py`
- Platform helpers: `pytron/platforms/pytron_os/*` and `pytron/platforms/*/ *_ops/*`
- Android: `pytron/platforms/android/*`

---

