import os
import pathlib
import mimetypes
import zipfile
from typing import Any, Optional, Tuple
from .base import WebviewComponent


class AssetComponent(WebviewComponent):
    """Handles in-memory asset caching, VAP archives, and binary serving."""

    def __init__(self, webview: Any):
        super().__init__(webview)
        self._served_data = {}

    def serve_data(self, key: str, data: bytes, mime_type: str) -> str:
        """
        Callback for serializing binary data used by plugins/VAP.
        Stores the data in memory to be served via protocol handlers.
        """
        # Ensure the key is clean (no leading slash or app/ prefix)
        clean_key = key.lstrip("/").replace("app/", "", 1)

        # PERFORMANCE: Limit cache size to prevent memory leaks from generated assets
        if len(self._served_data) > 500:
            # Simple purge of oldest entries if it gets too large
            keys_to_remove = list(self._served_data.keys())[:100]
            for k in keys_to_remove:
                del self._served_data[k]

        self._served_data[clean_key] = (data, mime_type)

        # Use appropriate scheme and ensure '/app/' prefix for protocol routing
        scheme = self.webview._routing_comp.scheme
        return f"{scheme}/app/{clean_key}"

    def serve_asset_callback(self, key: str) -> Optional[Tuple[bytes, str]]:
        """Called by Native Engine Protocol Handler to fetch VAP assets."""
        if key in self._served_data:
            return self._served_data[key]
        return None

    def load_vap_archive(self, archive_name: str):
        """Loads all assets from a .pytron archive into the VAP cache."""
        root_path = self.webview._routing_comp.root_path
        archive_path = pathlib.Path(root_path) / archive_name

        # Check if it's in _internal (common for PyInstaller)
        if not archive_path.exists():
            archive_path = pathlib.Path(root_path) / "_internal" / archive_name

        if not archive_path.exists():
            self.logger.warning(f"VAP Archive not found at {archive_path}")
            return

        self.logger.info(f"Loading VAP Archive: {archive_path}")
        try:
            with zipfile.ZipFile(archive_path, "r") as zipf:
                for name in zipf.namelist():
                    data = zipf.read(name)
                    mime, _ = mimetypes.guess_type(name)
                    self._served_data[name] = (data, mime or "application/octet-stream")
            self.logger.info(
                f"VAP: Loaded {len(self._served_data)} assets from archive."
            )
        except Exception as e:
            self.logger.error(f"Failed to load VAP archive: {e}")

    def get_binary_asset(self, key: str) -> Optional[dict]:
        """
        Retrieves an asset for the VAP bridge.
        Returns {'raw': <binary_string>, 'mime': <mime_type>} or None.
        """
        # 1. Check Memory Cache (_served_data)
        if key in self._served_data:
            data, mime = self._served_data[key]
            # Convert bytes to "latin-1" string for JS binary interop
            raw = data.decode("latin-1")
            return {"raw": raw, "mime": mime}

        # 2. Check File System (if key is a relative path)
        try:
            # Security: Prevent escaping app_root
            app_root = pathlib.Path(self.webview._app_root)
            possible_path = (app_root / key).resolve()
            if (
                str(possible_path).startswith(str(app_root))
                and possible_path.exists()
                and possible_path.is_file()
            ):
                mime, _ = mimetypes.guess_type(str(possible_path))
                with open(possible_path, "rb") as f:
                    data = f.read()
                    raw = data.decode("latin-1")
                    return {"raw": raw, "mime": mime or "application/octet-stream"}
        except Exception:
            pass

        return None
