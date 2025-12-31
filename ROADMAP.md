# Pytron Roadmap

This document outlines the planned features and improvements for Pytron.

## Q4 2025: Foundation & UI Stability
- [x] Global OS-level Shortcuts
- [x] Native System Tray & Menu Support
- [x] Native File Dialogs (Open/Save/Folder)
- [x] System Notifications (Toasts)
- [x] Lifecycle Hooks (`on_exit`)
- [x] Start on Boot support
- [x] Deep Linking (URI Schemes)
- [x] Binary IPC Bridge (`serve_data`)

## Q1 2026: Native UX & Professional Polish
- [ ] **Acrylic & Mica Support**: Native window transparency and blur effects.
- [ ] **Native File Drag-and-Drop**: Python-level events for dragging files onto the window.
- [ ] **File Associations**: Register `.pytron` or custom extensions to open with your app.
- [ ] **Native TitleBar V2**: Even tighter integration with Snap Layouts and OS themes.

## Q2 2026: Developer Experience (DX)
- [ ] **Multi-Window Support**: Inter-window communication and management.
- [ ] **Smart State Persistence**: Built-in SQLite sync for `app.state`.
- [ ] **Pytron Doctor UI**: In-app component for system health diagnostics.
- [ ] **Hot-Reloading V2**: Faster state-preserving reloads for complex apps.

## Future Vision
- [ ] **Mobile Support (Android/iOS)**: Move experimental Android build to stable.
- [ ] **WebAssembly (Wasm) Backend**: Run Python logic in the browser for web distribution.
- [ ] **Cloud Sync**: Secure, end-to-end encrypted state sync between devices.

---
*Note: This roadmap is subject to change based on community feedback and core maintainer focus and may be updated at any time.*
