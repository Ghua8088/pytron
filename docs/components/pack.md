Packaging & Build Pipeline (expanded)

Overview
- The `pack` subsystem is the heart of Pytron's packaging story: it gathers Python code, frontend assets, native engine artifacts, and optionally produces hardened or obfuscated payloads for distribution. Packaging is implemented as a small orchestration framework (see `pytron/pack/pipeline.py`) that composes modular build stages.

High-level goals
- Produce a working distributable (one-file, one-dir, or installer) that contains the Python runtime + application code + frontend assets + native engine(s).
- Support multiple backends (PyInstaller, Nuitka) and advanced hardening strategies (Rust `secure_loader`, Rust bootloader integration).
- Allow plugins and app code to participate in the package process (hooks, extra assets, hidden imports).

Key files
- [pytron/pack/pipeline.py](pytron/pack/pipeline.py) — pipeline orchestration, `BuildContext`, `BuildModule` abstraction.
- `pytron/pack/*` — modules that implement concrete build steps: `pyinstaller.py`, `nuitka.py`, `assets.py`, `secure.py`, `metadata.py`, `modules.py`, `compilers.py`, `rust_engine.py`, `secure_loader` related helpers.

Pipeline architecture 

1) BuildContext creation
- When `pytron package` runs, a `BuildContext` is created. It contains CLI args, paths (script, package_dir), bundling flags (`is_nuitka`, `is_onefile`, `is_secure`), and mutable lists for `add_data`, `hidden_imports`, `binaries`, `runtime_hooks`, and `pathex`.

2) Preparation phase (module.prepare)
- Each `BuildModule` has a `prepare(context)` hook. This is where modules scan the app, collect assets, compute hidden imports, generate manifest fragments, and register files to add to the bundle.
- Typical prepare modules:
	- AssetCollectorModule: gathers `frontend/dist`, plugin UI files, icons, and static assets. Supports VAP (virtual archive payload) creation.
	- ModuleScanner: inspects Python imports (and optionally AST/code analysis) to populate `hidden_imports` and `pathex` so downstream packers include everything.
	- NativeCollector: locates compiled Rust artifacts (`pytron_native`, `pytron_os`) and ensures they are copied into `pytron/dependencies` or into the bundle.
	- PluginHookCollector: calls `Plugin.invoke_package_hook(context)` to let plugins add hidden imports, runtime hooks, or extra data.

3) Build wrapper chaining (module.build_wrapper)
- The pipeline builds the actual executable by composing wrappers around the core build function. Each module can wrap the build call to add behavior before or after the core build.
- The wrapper chain is created in reverse so modules added earlier are the outer wrappers. This enables patterns like:
	- wrap with an "inject secure loader" step that modifies the final artifact after the core packer runs
	- wrap with "copy debug symbols" or "apply LTO/strip" steps

4) Core build execution
- The innermost function is the core build action (e.g., run PyInstaller or Nuitka). It typically does:
	- Generate spec/hook files.
	- Invoke the packer (`pyinstaller ...` or call Nuitka API/CLI) with `--add-data`, `--hidden-import`, `--paths`, and runtime hooks from `BuildContext`.
	- Produce a dist folder or single binary.

5) Post-build (module.post_build)
- After the core build returns success, the pipeline iterates modules in registration order and calls `post_build(context)`. Typical post-build tasks:
	- Patch the produced binary (inject resources, replace bootstrap code).
	- Run signing tools (codesign on macOS, signtool on Windows).
	- Create installer artifacts (NSIS script invocation, DMG creation, Debian packaging).
	- Create delta/patch artifacts (generate `app.pytron_patch` using bsdiff if requested).

Concrete modules & examples
- PyInstallerModule:
	- Generates a `.spec` reflecting `BuildContext` and calls `pyinstaller` with flags derived from CLI.
	- Adds hooks to collect frontend assets and copy `pytron/dependencies` into the bundled runtime.

- NuitkaModule:
	- Runs Nuitka with `--onefile` or `--output-dir`, configures `--include-package` and `--nofollow-import-to` to mimic PyInstaller behavior where applicable.
	- Nuitka often produces a more optimized binary; pipeline will handle packaging differences (one-file vs one-dir).

- SecureLoaderModule / RustLoaderModule:
	- Builds or bundles the Rust `secure_loader` (`pytron/pack/secure_loader`) and arranges the final executable so the loader sits in front of the Python payload.
	- Modifies environment variables and layout so `_internal`, `app.bundle`, and loader are colocated. May also embed the `app` module statically.

- AssetCollectorModule & VAP creation:
	- Optionally pack frontend files into a VAP archive (`app.pytron`) that the native protocol handler prefers. VAP allows read-only, uneditable payloads served via `pytron://app/`.
	- The Webview/native protocol supports serving in-memory assets via the `pytron_serve_asset` callback.

- RustEngineBundler:
	- Copies or rebuilds native engine artifacts (`pytron_native`, `pytron_os`) and ensures correct ABI/filename mapping for each target platform.

Compilation pipeline specifics (what makes it "crazy")
- ABI and Python extension stability: the pipeline must ensure compiled extensions match the target Python ABI. For cross-platform builds (e.g., building on CI for multiple OS/architectures) this involves cross-compilation, or building on dedicated runners.
- Multi-tool chaining: some flows use PyInstaller to make the executable, then a Rust loader is prepended; other flows use Nuitka to emit a single binary directly. The pipeline abstracts these via wrappers.
- Hook generation and hidden imports: dynamic Python imports require hook generation. The pipeline can use `collect_submodules` heuristics or explicit plugin-supplied hooks.
- Symbol stripping, LTO, and signing: for release builds the pipeline may enable LTO for Rust pieces, strip debug symbols from native libs, and run platform-specific signing utilities.

Plugin integration
- Plugins may register `on_package` hooks. During `prepare` they can add files to `add_data`, `hidden_imports`, or register runtime hooks. During `post_build` they can alter packaging outputs.

Diagnostics and reproducibility
- BuildContext captures all inputs; storing that context alongside produced artifacts (manifest + hash list) helps reproducible builds.
- For large builds, the pipeline supports progress reporting via the `context.progress` field.

Extending the pipeline
- To add a new backend or step, implement a `BuildModule` with `prepare`, `build_wrapper`, and `post_build` as needed and register it with `Pipeline.add_module()` before `Pipeline.run()`.

Commands & tips
- Run packaging with verbose logs to inspect what collectors added:

```bash
pytron package app.py --logger pytron_pkg.log --name MyApp --installer
```

- If native extensions fail at runtime, build and copy artifacts into `pytron/dependencies` and re-run packaging.

Compilers (pytron/pack/compilers.py)

- Purpose: Provides a path to produce a statically linked native executable from a Python entry script. Used by secure/hardened packaging flows that want a fused binary embedding a Python payload and a native bootloader.

- What it does (high-level):
	- Ensures build-time tools are available (`Cython`, `zig`).
	- Pre-processes the entry script so it can be Cythonized (patching the `if __name__ == '__main__'` block into an importable form).
	- Runs Cython to generate a C source file (`app.c`).
	- Appends compatibility stubs for Windows linking (`_fltused`, `WinMain`).
	- Invokes `zig build-exe` to statically link the generated C with a provided `bootloader_lib` and the Python runtime, platform-specific system libs, and produce a single `app` binary or `.exe`.

- Key functions (quick map):
	- `get_python_executable()` — returns the active Python interpreter path.
	- `ensure_cython(python_exe)` — verifies or installs `Cython` into the environment.
	- `find_zig()` — locates the `zig` binary (also checks for `ziglang` package binaries).
	- `cython_gen_c(script_path, build_dir, python_exe)` — produces `app.c` and applies compatibility patches.
	- `compile_c_to_executable(c_file, build_dir, zig_bin, python_exe, bootloader_lib)` — constructs and runs the `zig` compile/link command, handling host/target choices and platform linker flags.
	- `compile_script(script_path, build_dir, bootloader_lib)` — high-level orchestration used by the pipeline.

- Integration notes:
	- Expects a prepared/static `bootloader_lib` (the Rust loader or bootstrap library provided by `pytron/pack/secure_loader`).
	- Returns `None` on failure so the `pack` pipeline can fall back to other packers (PyInstaller/Nuitka) or emit informative errors.
	- Handles platform differences (Windows vs POSIX) including Python link names and system libs.

Files to inspect
- `pytron/pack/pipeline.py` — orchestrator and error handling
- `pytron/pack/pyinstaller.py`, `pytron/pack/nuitka.py` — concrete packers
- `pytron/pack/secure.py`, `pytron/pack/secure_loader` — hardening
- `pytron/plugin.py` — packaging hooks

Summary
- The pack pipeline is intentionally modular: collectors gather inputs, wrappers chain build steps, compilers provide a hardened native path, and post-build hooks finalize artifacts. This design supports the complex, multi-tool ecosystem required to produce cross-platform, hardened Pytron distributions.