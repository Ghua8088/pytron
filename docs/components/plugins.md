Plugins

Responsibilities
- Provide extensibility: Python logic and optional UI assets.
- Allow isolated or in-process execution with lifecycle hooks and package-time hooks.

Key file
- [pytron/plugin.py](pytron/plugin.py)

Interactions
- Discovered by `App` during startup; loaded with a `SupervisedApp` proxy to protect host.
- Can declare Python/npm deps; install helpers exist for both.
- Hooks: `on_package` for build-time integration.

Notes
- Plugin manifests use `manifest.json` and optional `ui_entry` for frontend assets.