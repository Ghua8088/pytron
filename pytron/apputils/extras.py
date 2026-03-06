import os
from ..tray import SystemTray


class ExtrasMixin:
    def load_plugin(self, manifest_path):
        from ..plugin import Plugin, PluginError

        try:
            plugin = Plugin(manifest_path)
            plugin.check_dependencies()
            plugin.load(self)
            self.plugins.append(plugin)
            self.logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")
        except PluginError as e:
            self.logger.error(f"Failed to load plugin from {manifest_path}: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error loading plugin from {manifest_path}: {e}"
            )

    def _resolve_icon_path(self, icon_path):
        """
        Robustly resolves the icon path, checking absolute paths,
        config-relative paths, and the bundled 'resources/app_icon' fallback.
        """
        if not icon_path:
            return None

        resolved = icon_path
        if not os.path.isabs(icon_path):
            resolved = os.path.join(self.app_root, icon_path)

        # Check if strictly exists
        if os.path.exists(resolved):
            return resolved

        # Fallback to bundled resource
        for ext in [".ico", ".png", ".icns"]:
            fallback = os.path.join(self.app_root, "resources", f"app_icon{ext}")
            if os.path.exists(fallback):
                return fallback

        return resolved  # Return best guess if fallback fails

    def setup_tray(self, title=None, icon=None):
        if not title:
            title = self.config.get("title", "Pytron")
        if not icon and "icon" in self.config:
            icon = self.config["icon"]

        icon = self._resolve_icon_path(icon)
        self.tray = SystemTray(title, icon)
        return self.tray

    def setup_tray_standard(self, title=None, icon=None):
        if not title:
            title = self.config.get("title", "Pytron")
        if not icon and "icon" in self.config:
            icon = self.config["icon"]
        icon = self._resolve_icon_path(icon)

        # For the native engine we want close-to-tray window behaviour, but we do NOT
        # delegate the icon+menu to the C++ layer because it has no API for custom items.
        # Python SystemTray owns the Shell_NotifyIcon and popup menu on every engine.
        if hasattr(self, "engine") and self.engine == "native":
            if self.windows:
                # Windows already exist — configure close-to-tray directly.
                for w in self.windows:
                    w.config["close_to_tray"] = True
                    try:
                        w.set_prevent_close(True)
                    except Exception:
                        pass
            else:
                # Windows not ready yet — queue just the close_to_tray flag so
                # webview.start() picks it up without creating a native tray icon.
                self.config["_pending_close_to_tray"] = True

        # Python SystemTray always handles the icon and popup menu.
        tray = self.setup_tray(title, icon)
        tray.add_item("Show App", self.show)
        tray.add_item("Hide App", self.hide)
        tray.add_separator()
        tray.add_item("Quit", self.quit)

        # If run() has already started (called from a frontend-exposed function),
        # kick off the tray immediately.  Otherwise run() will start it.
        if getattr(self, "is_running", False) and not tray._running:
            tray.start(self)

        return tray
