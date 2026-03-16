**Serializer**

- **Purpose:** Encode/decode Python state and specific app data shapes to disk or for IPC. Provides a canonical format for saving small persisted blobs and exchanging structured messages across the Python↔native boundary.

- **Key file:** `pytron/serializer.py`

- **Responsibilities:**
  - Provide stable, version-tolerant serialization for app state and plugin metadata.
  - Offer helpers to snapshot state for packaging manifests and reproducible builds.

- **Integration points:** Used by `pytron/state.py` to persist state, and by pack/installer code to write manifest files.

- **What to read next:** `pytron/serializer.py`, `pytron/state.py`, and `pytron/pack/pipeline.py`.
