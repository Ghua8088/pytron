import os
import json
import sys
import importlib
import logging
import subprocess
import threading
import traceback
from typing import List, Dict, Any, Union


class PluginError(Exception):
    pass


class PluginStorage:
    """Provides a plugin with its own private JSON storage and data folder."""

    def __init__(self, app_instance, plugin_name):
        self._app = app_instance
        self._name = plugin_name
        self._dir = os.path.join(self._app.storage_path, "plugins", self._name)
        os.makedirs(self._dir, exist_ok=True)
        self._file = os.path.join(self._dir, "data.json")

    def set(self, key, value):
        data = self._read()
        data[key] = value
        self._write(data)

    def get(self, key, default=None):
        data = self._read()
        return data.get(key, default)

    def delete(self, key):
        data = self._read()
        if key in data:
            del data[key]
            self._write(data)

    def path(self, *suffixes):
        """Returns an absolute path to a file in the plugin's private folder."""
        path = os.path.join(self._dir, *suffixes)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def _read(self):
        if not os.path.exists(self._file):
            return {}
        try:
            with open(self._file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def _write(self, data):
        with open(self._file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)


class SupervisedApp:
    """
    A proxy for the App instance that protects the main app from plugin crashes.
    """

    def __init__(self, app, plugin_name):
        self._app = app
        self._plugin_name = plugin_name
        self.logger = logging.getLogger(f"Pytron.Plugin.{plugin_name}.Supervisor")
        self.storage = PluginStorage(app, plugin_name)

    def expose(self, func, name=None, secure=False):
        """Wraps the exposed function in an error handler."""
        func_name = name or func.__name__

        def safe_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.logger.error(
                    f"Plugin '{self._plugin_name}' crashed in '{func_name}': {e}"
                )
                self.logger.debug(traceback.format_exc())
                return {"error": "Plugin Execution Failed", "message": str(e)}

        return self._app.expose(safe_wrapper, name=name, secure=secure)

    def __getattr__(self, name):
        # Delegate everything else (state, broadcast, etc.) to the real app
        return getattr(self._app, name)


class Plugin:
    """
    Represents a loaded Pytron Plugin.
    """

    def __init__(self, manifest_path: str):
        self.manifest_path = os.path.abspath(manifest_path)
        self.directory = os.path.dirname(self.manifest_path)
        self.manifest = self._load_manifest()
        self.logger = logging.getLogger(f"Pytron.Plugin.{self.name}")

    def _load_manifest(self) -> Dict[str, Any]:
        if not os.path.exists(self.manifest_path):
            raise PluginError(f"Manifest not found at {self.manifest_path}")

        try:
            with open(self.manifest_path, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise PluginError(f"Invalid JSON in manifest: {e}")

        required_fields = ["name", "version", "entry_point"]
        for field in required_fields:
            if field not in data:
                raise PluginError(f"Manifest missing required field: {field}")

        return data

    @property
    def name(self) -> str:
        return self.manifest.get("name", "unknown")

    @property
    def version(self) -> str:
        return self.manifest.get("version", "0.0.0")

    @property
    def python_dependencies(self) -> List[str]:
        return self.manifest.get("python_dependencies", [])

    @property
    def npm_dependencies(self) -> Dict[str, str]:
        return self.manifest.get("npm_dependencies", {})

    @property
    def entry_point(self) -> str:
        return self.manifest.get("entry_point")

    @property
    def ui_entry(self) -> str:
        """Relative path to the JS/WebComponent entry point for this plugin."""
        return self.manifest.get("ui_entry")

    @property
    def isolated(self) -> bool:
        """Whether this plugin should run in its own process/venv."""
        return self.manifest.get("isolated", False)

    def check_dependencies(self) -> bool:
        """
        Checks if Python dependencies are installed.
        Returns True if all dependencies are present.
        """
        missing = []
        for dep in self.python_dependencies:
            try:
                importlib.import_module(dep)
            except ImportError:
                missing.append(dep)

        if missing:
            self.logger.warning(f"Missing Python dependencies: {', '.join(missing)}")
            return False

        return True

    def install_dependencies(self, frontend_dir: str = None):
        """
        Attempts to install missing Python and NPM dependencies.
        """
        # 1. Python Dependencies
        py_deps = self.python_dependencies
        if py_deps:
            self.logger.info(
                f"Installing Python dependencies for {self.name}: {py_deps}"
            )
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install"] + py_deps
                )
                self.logger.info("Python dependencies installed successfully.")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to install Python dependencies: {e}")
                raise PluginError(f"Python dependency installation failed: {e}")

        # 2. NPM Dependencies
        npm_deps = self.npm_dependencies
        if npm_deps and frontend_dir:
            if not os.path.exists(frontend_dir):
                self.logger.warning(
                    f"Frontend directory not found at {frontend_dir}. Skipping NPM dependencies."
                )
                return

            self.logger.info(
                f"Installing NPM dependencies for {self.name} in {frontend_dir}..."
            )
            pkg_list = [f"{name}@{ver}" for name, ver in npm_deps.items()]

            try:
                npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
                # Use --no-save to keep the main package.json clean if preferred,
                # but usually plugins need them bundled.
                subprocess.check_call([npm_cmd, "install"] + pkg_list, cwd=frontend_dir)
                self.logger.info(
                    f"NPM dependencies for {self.name} installed successfully."
                )
            except Exception as e:
                self.logger.error(f"Failed to install NPM dependencies: {e}")
                # We don't necessarily want to crash the whole app if NPM is missing,
                # but we should log it.

    def load(self, app_instance):
        """
        Loads the entry point and runs initialization.
        """
        # Ensure we use an absolute path for sys.path to avoid issues after os.chdir
        plugin_dir = os.path.abspath(self.directory)
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)

        entry_str = self.entry_point
        if ":" not in entry_str:
            raise PluginError(
                f"Invalid entry_point format '{entry_str}'. Expected 'module:function' or 'module:Class'"
            )

        module_name, object_name = entry_str.split(":")

        # Create the Supervised proxy
        supervised_app = SupervisedApp(app_instance, self.name)

        try:
            # Import the module
            self.module = importlib.import_module(module_name)

            # Get the object
            if not hasattr(self.module, object_name):
                raise PluginError(
                    f"Entry point '{object_name}' not found in module '{module_name}'"
                )

            entry_obj = getattr(self.module, object_name)

            def init_plugin():
                try:
                    # 1. If it's a function, call it with `supervised_app`
                    if callable(entry_obj) and not isinstance(entry_obj, type):
                        self.logger.info(
                            f"Initializing plugin '{self.name}' via function '{object_name}'"
                        )
                        self.instance = entry_obj(supervised_app)

                    # 2. If it's a class, instantiate it with `supervised_app`
                    elif isinstance(entry_obj, type):
                        self.logger.info(
                            f"Initializing plugin '{self.name}' via class '{object_name}'"
                        )
                        self.instance = entry_obj(supervised_app)
                        # If the class has a 'setup' method, call it
                        if hasattr(self.instance, "setup"):
                            self.instance.setup()
                except Exception as e:
                    self.logger.error(f"Plugin '{self.name}' initialization crash: {e}")
                    self.logger.debug(traceback.format_exc())

            if self.isolated:
                self.logger.info(
                    f"Plugin '{self.name}' is isolated. Starting in worker thread..."
                )
                thread = threading.Thread(
                    target=init_plugin, name=f"Plugin-{self.name}", daemon=True
                )
                thread.start()
            else:
                init_plugin()

        except Exception as e:
            raise PluginError(f"Failed to load plugin '{self.name}': {e}")

    def unload(self):
        """
        Unloads the plugin by calling its teardown method if available.
        """
        if hasattr(self, "instance") and self.instance:
            if hasattr(self.instance, "teardown"):
                try:
                    self.instance.teardown()
                    self.logger.info(f"Plugin '{self.name}' torn down successfully.")
                except Exception as e:
                    self.logger.error(f"Error tearing down plugin '{self.name}': {e}")
            self.instance = None

        if hasattr(self, "module") and self.module:
            # We can't really 'unimport' in Python reliably, but we can clean up references
            del self.module

        # Optional: Remove directory from sys.path?
        # Risky if other plugins share it or if user reloads.

    def invoke_package_hook(self, context: Dict[str, Any]):
        """
        Invoked during 'pytron package'. Allows plugins to add extra data,
        hidden imports, or run custom build scripts.
        """
        if hasattr(self, "instance") and hasattr(self.instance, "on_package"):
            try:
                self.logger.info(f"Invoking on_package hook for '{self.name}'...")
                self.instance.on_package(context)
            except Exception as e:
                self.logger.error(f"Error in on_package hook for '{self.name}': {e}")
                self.logger.debug(traceback.format_exc())


def discover_plugins(plugins_dir: str) -> List[Plugin]:
    """
    Utility to find all plugins in a directory without loading them.
    """
    plugins = []
    if not os.path.exists(plugins_dir):
        return plugins

    for item in os.listdir(plugins_dir):
        plugin_path = os.path.join(plugins_dir, item)
        manifest_path = os.path.join(plugin_path, "manifest.json")
        if os.path.isdir(plugin_path) and os.path.exists(manifest_path):
            try:
                plugins.append(Plugin(manifest_path))
            except Exception:
                pass
    return plugins
