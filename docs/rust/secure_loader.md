Secure Loader (Rust)

Location
- `pytron/pack/secure_loader` (Cargo project)

Purpose
- A Rust-based launcher/loader used to provide a hardened, minimal native host for packaged Pytron apps.
- Responsibilities: anti-debugging checks, patch application (BSDIFF), environment isolation, embedded settings handling, and running the Python payload with a statically-registered binary module.

Key files
- `src/lib.rs` — entrypoint for the loader; registers the compiled `app` extension into Python (`PyImport_AppendInittab`), applies patches, initializes COM (Windows), and prepares `PYTHONHOME`/`PYTHONPATH` before calling into `run_python_and_payload`.
- `src/security.rs` — anti-debugging and runtime integrity checks (Windows-specific checks such as IsDebuggerPresent, CheckRemoteDebuggerPresent, timing checks). Exits the process on detection.
- `src/patcher.rs` — applies binary patches (BSDIFF) to an existing payload (`app.pytron`) using safe temp-file replace strategy.
- `src/python_runtime.rs` — prepares Python interpreter (freethreaded), manipulates `sys.path` and `sys.argv`, sets `_MEIPASS` to the internal folder, and imports the compiled `app` module to start application logic.
- `src/config.rs` — loads bundled `settings.json` (or embedded JSON), returns `Settings` struct.
- `src/ui.rs` — small native UI helpers (alerts, COM init, app id) to show fatal dialogs when errors occur.
- `build_loader.py` — Python helper used during packaging to compile/assemble the loader binary.

Integration points & flow
1. Packager builds the Rust `secure_loader` and places it alongside `app.bundle` and `_internal` folder inside the packaged app.
2. On launch, `secure_loader` runs first; it performs anti-debug checks, applies any `app.pytron_patch`, adjusts environment variables to point Python to `_internal`, and registers the statically linked `app` module.
3. The loader calls into `run_python_and_payload` which uses pyo3 to initialize Python and import `app`, letting the packaged application logic run inside the isolated environment.

Security notes
- Anti-debugging is primarily Windows-focused; timing checks and immediate process exit are used when tampering is suspected.
- Patching uses BSDIFF; the patch application is atomic (writes to tmp then rename) to avoid corrupting payloads.
- The loader aggressively clears `PYTHONPATH`/`PYTHONHOME` and sets `PYTHONNOUSERSITE` and `PYTHONUTF8` to ensure deterministic runtime.

When to review
- If you need to audit or adapt packaging hardening, review `security.rs` and `python_runtime.rs` for environment handling and any platform-specific calls.
- If supporting additional OS hardening, mirror the Windows checks with platform-appropriate techniques in `security.rs`.