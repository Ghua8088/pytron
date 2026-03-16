Prerequisites for contributing to Pytron-kit

Purpose
- This document lists the tools, runtimes, knowledge, and quick setup steps a developer needs to effectively work on, build, test, and package Pytron-kit.

Core knowledge and expectations
- Comfortable with Python 3.11+ (project uses modern Python features). Familiarity with virtual environments and `pip`.
- Familiarity with Rust and Cargo (the codebase contains multiple Rust crates: `pytron_native`, `pytron_os`, `secure_loader`).
- Basic C/C++/linker concepts (extension ABI, link flags, symbol issues) helpful for native integration and debugging.
- Web frontend build basics (Node.js, npm/yarn) for building `frontend/dist` assets used by example apps and the UI.

Required software
- Python
  - Version: 3.11+ recommended (use the same minor version locally as CI/tests).
  - Tools: `venv` or virtualenv, `pip`.

- Rust toolchain
  - Install `rustup` and a stable toolchain. `cargo build` is used for native crates.
  - Optional: `rustfmt`, `clippy` for linting.

- Zig
  - Required for the Cython→C→static-binary compilation path (see `pytron/pack/compilers.py`).
  - Install from https://ziglang.org/ and ensure `zig` is on `PATH`.

- C compiler / build tools
  - Windows: Visual Studio Build Tools (MSVC) with C/C++ toolchain and SDK.
  - macOS: Xcode command line tools.
  - Linux: `build-essential` (gcc/clang, make), development headers.

- Android SDK / NDK (for Android builds)
  - Required for cross-compiling Android wheels and installers. The project may use Zig + NDK helpers; follow `pytron/platforms/android/builder.py` for exact setup.

- Java JDK (for Android tooling)

- Node.js + npm or Yarn
  - For building frontend examples (files under `examples/*` and `frontend/src`).

- Cython
  - Used by the `compilers` path. The build helper will attempt to install it automatically into the environment, but you can pre-install with `pip install Cython`.

- PyInstaller and/or Nuitka
  - Packaging backends. Install per your preferred pipeline: `pip install pyinstaller` or `pip install nuitka`.

- Optional tools
  - LIEF (binary inspection/repair) — used in some Android packaging flows.
  - bsdiff/bsdiff4 — for creating delta patches.

Repository structure pointers (what to read first)
- `pytron/application.py` — app lifecycle and main entry.
- `pytron/webview.py` — webview wrapper and IPC glue.
- `pytron/pack/pipeline.py` — pack orchestration, `BuildContext`, and module registration.
- `pytron/pack/compilers.py` — Cython + Zig static compilation path (now summarized in docs/components/pack.md).
- `pytron/pack/secure_loader` — Rust-based loader used for hardened packages.
- `pytron/engines/native/` and `pytron/platforms/` — native engine sources and platform-specific operations.
- `pyproject.toml` and `pytron_kit.egg-info/` — Python packaging metadata and dependency lists.

Quick dev setup (Windows example)

```powershell
# create and activate venv (Windows)
python -m venv .venv
.\.venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
# install optional pack tools
pip install pyinstaller cython
```

Quick dev setup (POSIX)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install pyinstaller cython
```

Running the app locally
- Start a local dev run (uses the selected web engine):

```bash
pytron run --chrome
```

Running tests
- The test suite uses `pytest`. Run:

```bash
pytest -q
```

Building native Rust crates
- Use `cargo build` from the crate directory, or rely on the build helpers in `pytron/engines/native/build.py`.

Packaging / producing a release
- See `pytron/pack/pipeline.py` and `docs/components/pack.md` for the full pipeline.
- Example (pack with PyInstaller):

```bash
pytron package path/to/app.py --backend pyinstaller --name MyApp
```

Cross-compilation notes
- Building sealed native binaries with `zig` (the `compilers` flow) performs static linking and requires matching Python dev headers and lib availability for the target.
- For Android and other platforms, prefer building on platform-specific runners or use configured cross toolchains (see `pytron/platforms/android/builder.py`).

Editor / tooling suggestions
- Use VS Code or JetBrains IDEs with Python and Rust plugins. Configure the workspace interpreter to your venv.
- Enable formatters/lints: `black`, `ruff`, `mypy` (if used in CI).

Debugging tips
- If native extensions fail to load, check the Python ABI (major/minor) and inspect `pytron/dependencies` for platform-specific artifacts.
- Use `ldd` / `otool -L` / `dumpbin` to inspect native library dependencies.

CI / reproducible builds
- The repo's CI defines the build matrix; follow the `pyproject.toml` and any `*.github/workflows/*` for exact OS/toolchain combos.
- For reproducible packaging, capture `BuildContext` outputs (manifest + hashes) and use dedicated runners for each target.

Where to get help
- Read the `docs/` folder first — it contains per-component guides and the `ARCHITECTURE.md` overview.
- For build-specific issues inspect logs printed by `pytron package` and the backend (PyInstaller/Nuitka/Zig/Cargo).

Next steps after setup
- Build an example app from `examples/01-hello-world` and run it.
- Experiment with `pytron package` using `--dry-run` or verbose flags to inspect what the pipeline collects.

Contact & contribution etiquette
- Follow repository `CONTRIBUTING.md` and run the test suite before opening PRs.

This file should be kept current as build tools and required versions change.
