import os
import sys
from typing import Any, List

from ..plugin import Plugin
from .component import AppComponent


class PluginComponent(AppComponent):
    """Handles plugin discovery, dependency management, and lifecycle."""

    def __init__(self, app: Any):
        super().__init__(app)
        self.plugin_statuses: List[dict] = []

    def discover_and_load(self):
        """Standard discovery logic moved from App.__init__."""
        base_dir = self._app.app_root

        # Plugin Discovery: Check both bundled (internal) and drop-in (external) paths
        candidate_dirs = []
        if getattr(sys, "frozen", False):
            # 1. Bundled plugins inside _internal
            if hasattr(sys, "_MEIPASS"):
                candidate_dirs.append(os.path.join(sys._MEIPASS, "plugins"))
            # 2. Drop-in plugins next to the EXE
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            candidate_dirs.append(os.path.join(exe_dir, "plugins"))
        else:
            # Local dev plugins next to the script
            candidate_dirs.append(os.path.join(base_dir, "plugins"))

        custom_plugins_dir = self._app.config.get("plugins_dir")
        if custom_plugins_dir:
            if not os.path.isabs(custom_plugins_dir):
                custom_plugins_dir = os.path.join(base_dir, custom_plugins_dir)
            candidate_dirs.append(custom_plugins_dir)

        # Remove duplicates and resolve
        seen = set()
        for p_dir in candidate_dirs:
            p_dir = os.path.abspath(p_dir)
            if p_dir not in seen and os.path.exists(p_dir):
                self._app.logger.info(f"Scanning for plugins in: {p_dir}")
                self.load_plugins(p_dir)
                seen.add(p_dir)

    def load_plugins(self, plugins_dir: str):
        """Discovers and loads plugins from the specified directory."""
        if not os.path.exists(plugins_dir):
            self._app.logger.warning(f"Plugins directory not found: {plugins_dir}")
            return

        # Initialize plugin list in state if not present
        if not hasattr(self._app.state, "plugins"):
            self._app.state.plugins = []

        # Resolve frontend dir for NPM dependency installation
        frontend_dir = os.path.join(self._app.app_root, "frontend")
        if not os.path.exists(frontend_dir):
            potential = os.path.join(
                self._app.app_root, self._app.config.get("url", "").split("/")[0]
            )
            if os.path.exists(os.path.join(potential, "package.json")):
                frontend_dir = potential

        allowed_plugins = self._app.config.get("plugins", [])
        scan_items = []

        if (
            allowed_plugins
            and isinstance(allowed_plugins, list)
            and len(allowed_plugins) > 0
        ):
            scan_items = allowed_plugins
        else:
            scan_items = sorted(os.listdir(plugins_dir))

        for item in scan_items:
            plugin_path = os.path.join(plugins_dir, item)
            manifest_path = os.path.join(plugin_path, "manifest.json")

            if os.path.isdir(plugin_path) and os.path.exists(manifest_path):
                try:
                    self._app.logger.info(f"Loading plugin from {plugin_path}...")
                    plugin = Plugin(manifest_path)

                    if not plugin.check_dependencies() or (
                        plugin.npm_dependencies and not plugin.check_js_dependencies()
                    ):
                        self._app.logger.info(
                            f"Installing dependencies for {plugin.name}..."
                        )
                        provider = self._app.config.get("frontend_provider", "npm")
                        plugin.install_dependencies(
                            frontend_dir=frontend_dir, provider=provider
                        )

                    plugin.load(self._app)
                    self._app.plugins.append(plugin)

                    # Metadata for frontend
                    plugins_list = list(self._app.state.plugins or [])
                    base_url = self._app.get_base_url()
                    plugin_meta = {
                        "name": plugin.name,
                        "version": plugin.version,
                        "ui_entry": (
                            f"{base_url}/app/plugins/{item}/{plugin.ui_entry}"
                            if plugin.ui_entry
                            else None
                        ),
                        "slot": plugin.manifest.get("slot"),
                    }
                    plugins_list.append(plugin_meta)
                    self._app.state.plugins = plugins_list

                    self.plugin_statuses.append(
                        {
                            "name": plugin.name,
                            "status": "loaded",
                            "version": plugin.version,
                            "path": plugin_path,
                        }
                    )
                    self._app.publish("pytron:plugin-loaded", plugin_meta)

                except Exception as e:
                    self.plugin_statuses.append(
                        {
                            "name": item,
                            "status": "error",
                            "error": str(e),
                            "path": plugin_path,
                        }
                    )
                    self._app.logger.error(
                        f"Failed to load plugin at {plugin_path}: {e}"
                    )

    def unload_plugins(self):
        """Unloads all loaded plugins."""
        for plugin in self._app.plugins:
            try:
                plugin.unload()
            except Exception as e:
                self._app.logger.error(f"Error unloading plugin {plugin.name}: {e}")
        self._app.plugins.clear()
        self.plugin_statuses.clear()
