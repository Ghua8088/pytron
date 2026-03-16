**Shortcuts & Menu**

- **Purpose:** Handle global and app-level keyboard shortcuts and native menu building across platforms.

- **Key files:** `pytron/shortcuts.py`, `pytron/menu.py`

- **Responsibilities:**
  - Register and manage keyboard accelerators and global hotkeys.
  - Build native menus or application menus appropriate to the host platform.
  - Provide plumbing so menu actions and shortcuts dispatch events into the main `pytron` application and plugin handlers.

- **Platform notes:** Implementations deal with platform differences (macOS menu bar semantics, Windows accelerators, Linux desktop variations). Most platform-specific behavior is delegated to the `pytron/platforms/*` modules where necessary.

- **Integration points:** `pytron/application` wires shortcuts and menu items during startup; `pytron/webview` can expose menu-triggered actions to the UI.

- **What to read next:** `pytron/shortcuts.py`, `pytron/menu.py`, and `pytron/platforms/` implementations.
