from typing import Any


class WebviewComponent:
    """Base class for all discrete Webview capabilities (IPC, Assets, etc.)."""

    def __init__(self, webview: Any):
        self._webview = webview

    @property
    def webview(self):
        return self._webview

    @property
    def native(self):
        return self._webview.native

    @property
    def logger(self):
        return self._webview.logger
