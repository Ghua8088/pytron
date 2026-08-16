import pathlib
import sys
import urllib.parse
from typing import Any

from .base import WebviewComponent


class RoutingComponent(WebviewComponent):
    """Handles URL normalization, scheme resolution, and path mapping."""

    def __init__(self, webview: Any):
        super().__init__(webview)
        self.root_path = self._determine_root_path()
        self.scheme = self._determine_scheme()

    def _determine_root_path(self) -> str:
        """Determines the definitive application root path."""
        wv = self.webview
        if wv.app and hasattr(wv.app, "app_root") and wv.app.app_root:
            return str(wv.app.app_root)

        # Fallback to sys._MEIPASS or CWD
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return str(pathlib.Path(sys._MEIPASS))
        return str(pathlib.Path.cwd())

    def _determine_scheme(self) -> str:
        """Determines the appropriate protocol scheme (pytron:// or https://)."""
        config = self.webview.config
        if config.get("engine") == "chrome":
            return "pytron://localhost"

        # Windows Native Engine requires https:// for WebView2 custom protocols
        return (
            "https://pytron.localhost"
            if sys.platform == "win32"
            else "pytron://localhost"
        )

    def normalize_to_pytron(self, url: str) -> str:
        """Ensures local file paths are converted to pytron://app/ URLs relative to root_path."""
        if url.startswith(("http:", "https:", "pytron:", "data:", "about:")):
            return url

        path_obj = pathlib.Path(url)
        if not path_obj.is_absolute():
            path_obj = (pathlib.Path(self.root_path) / path_obj).resolve()

        # Check if it resides within root_path
        try:
            root = pathlib.Path(self.root_path).resolve()
            # relative_to throws ValueError if not relative
            rel = path_obj.resolve().relative_to(root)
            # Use forward slashes for URL
            return f"{self.scheme}/app/{urllib.parse.quote(rel.as_posix())}"
        except (ValueError, Exception):
            # If outside root, we can't serve it via pytron:// easily (Native engine locks root)
            self.logger.warning(
                f"Navigate path {url} is outside protocol root {self.root_path}. "
                "Falling back to raw path."
            )
            return str(path_obj)

    def normalize_config_url(self, config: dict):
        """Standardizes the URL in the provided config dict (Legacy support)."""
        raw_url = config.get("url")
        if not raw_url:
            return

        if raw_url.startswith(("http:", "https:", "pytron:")):
            return

        path_obj = pathlib.Path(raw_url)
        if not path_obj.is_absolute():
            path_obj = (pathlib.Path(self.root_path) / path_obj).resolve()

        # Convert to pytron:// with localhost authority
        config["url"] = path_obj.as_uri().replace("file:///", "pytron://localhost/")
