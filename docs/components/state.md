**State**

- **Purpose:** Centralized runtime state management used by the app and its plugins. Keeps persisted and ephemeral application state consistent across components.

- **Key file:** `pytron/state.py`

- **Responsibilities:**
  - Expose a serializable state container with change notifications.
  - Persist small amounts of configuration or session state between runs (if configured).
  - Provide thread-safe accessors for UI/native threads.

- **Typical usage:** Components read/write state via the `State` object; UI bindings or plugins register listeners to react to changes.

- **What to read next:** `pytron/state.py`, `pytron/plugin.py` (for how plugins interact with state).
