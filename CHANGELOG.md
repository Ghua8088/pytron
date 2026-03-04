# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.14] - 2026-02-08

### Added
- **Credits & Acknowledgments**: Added `CREDITS.md` to honor third-party dependencies (Wry, Tao, Electron, etc.).
- **Support Documentation**: Added `SUPPORT.md` for better community guidance.
- **Improved Manifest**: Updated `MANIFEST.in` to include all documentation and internal architecture files.

### Changed
- **License Rollback**: Reverted to pure Apache 2.0 based on community feedback. We value our open-source roots!
- Refined the packaging pipeline documentation to clarify "Safe" vs "Unsafe" methods in `SECURITY.md`.
- Updated repository metadata in `pyproject.toml` to reflect the current license status.

## [0.3.x] - Earlier Releases

### Added
- **Agentic Shield**: Introduced the new Rust-based secure bootloader.
- **Crystal Audit**: Runtime-audited dependency mapping for 100% accurate builds.
- **Dual Engine Support**: Optional transition between Native Webview (Wry) and Chrome Engine (Electron).
- **Zero-Copy Bridge**: High-speed binary data streaming via `pytron://`.

---
*Note: For older version details, please refer to the GitHub release tags.*
