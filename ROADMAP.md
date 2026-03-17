# Pytron Roadmap

This document outlines the planned features and improvements for Pytron.

## Current Phase: The "Hydraulic" Transition (Q1 2026)
We are currently bridging the gap between legacy Python wrappers and a hardened Rust-native core.

- [x] **Linux GLib Schism Fix**: Stabilized symbol collisions through environment sanitization and guarded native loading.
- [x] **X11 Stability**: Forced X11 backends for virtualized environments (VMware/Pop!_OS).
- [ ] **Native OS Core (pytron_os) Lockdown**: Strip all GTK/GObject dependencies from `pytron_os` on Linux. Switch to pure **X11 Atoms** for window management and **DBus/ZBus** for Tray/Notifications.
- [ ] **Engine Isolation**: Ensure the replaceable engines (Native/Chrome/Servo) can be swapped without touching the global process state owned by `pytron_os`.

## Q2 2026: The "Monolithic Core" strategy
To solve distribution and stability issues across Linux distros, we will move toward a unified native runtime.

- [ ] **Unified Native Core**: Consolidate `pytron_native` and `pytron_os` into a single monolithic Rust extension to eliminate symbol collisions once and for all.
- [ ] **Acrylic & Mica (Windows)**: Full native DWM support for Windows 11 transparency effects.
- [ ] **Native File Drag-and-Drop**: Python-level events piped through the Rust event loop.

## Q3 2026: Developer Experience & Ecosystem
- [ ] **Multi-Window V2**: Shared Context management for multi-window applications.
- [ ] **Pytron Doctor**: Advanced system diagnostic CLI to fix missing native headers/libraries.
- [ ] **Hot-Reloading V2**: State-preserving reloads for complex ReactiveState apps.

## Future Vision: "Universal Pytron"
- [ ] **Mobile Stability (Android/iOS)**: Move experimental Android build to a first-class citizen.
- [ ] **Wasm Extension Layer**: Allow Python logic to call into Wasm modules for high-speed processing.
- [ ] **Cloud-Encrypted State**: End-to-end encrypted sync for `ReactiveState` across multiple Pytron instances.

---
*Note: This roadmap reflects our focus on OS-level deep integration and architectural stability.*
