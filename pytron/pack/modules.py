import os
import sys
import json
import shutil
from pathlib import Path
from .pipeline import BuildModule, BuildContext
from ..console import log
from .assets import get_smart_assets
from .metadata import MetadataEditor


class AssetModule(BuildModule):
    def prepare(self, context: BuildContext):
        log("Gathering project assets...", style="dim")

        # 1. settings.json
        settings_path = context.script_dir / "settings.json"
        if settings_path.exists():
            # Force debug=False for production
            clean_settings = context.settings.copy()
            if clean_settings.get("debug") is True:
                clean_settings["debug"] = False

            temp_settings_dir = context.build_dir / "pytron_assets"
            temp_settings_dir.mkdir(parents=True, exist_ok=True)
            temp_settings_path = temp_settings_dir / "settings.json"
            temp_settings_path.write_text(json.dumps(clean_settings, indent=4))

            context.add_data.append(f"{temp_settings_path}{os.pathsep}.")

        # 2. Frontend Dist
        possible_dists = [
            context.script_dir / "frontend" / "dist",
            context.script_dir / "frontend" / "build",
        ]
        frontend_dist = None
        for d in possible_dists:
            if d.exists() and d.is_dir():
                frontend_dist = d
                break

        if frontend_dist:
            rel_path = frontend_dist.relative_to(context.script_dir)
            context.add_data.append(f"{frontend_dist}{os.pathsep}{rel_path}")

        # 3. Smart Assets
        # (This is a simplified version of what was in package.py)
        if getattr(context, "smart_assets", False):
            try:
                smart = get_smart_assets(
                    context.script_dir, frontend_dist=frontend_dist
                )
                if smart:
                    context.add_data.extend(smart)
            except Exception as e:
                log(f"Warning: Smart assets failed: {e}", style="warning")


class EngineModule(BuildModule):
    def prepare(self, context: BuildContext):
        if context.engine != "chrome":
            return

        log(f"Configuring {context.engine} engine...", style="dim")

        # Global engine path
        global_engine_path = Path.home() / ".pytron" / "engines" / "chrome"
        if global_engine_path.exists():
            log(f"Auto-bundling Chrome Engine binaries", style="dim")
            # Bundle into pytron/dependancies/chrome
            dest_dep = os.path.join("pytron", "dependancies", "chrome")
            context.add_data.append(f"{global_engine_path}{os.pathsep}{dest_dep}")

            # Bundle shell source
            shell_src = context.package_dir / "pytron" / "engines" / "chrome" / "shell"
            if shell_src.exists():
                shell_dest = os.path.join("pytron", "engines", "chrome", "shell")
                context.add_data.append(f"{shell_src}{os.pathsep}{shell_dest}")
        else:
            log(
                "Error: Chrome engine not found. Run 'pytron engine install chrome'",
                style="error",
            )

    def post_build(self, context: BuildContext):
        if context.engine != "chrome" or sys.platform != "win32":
            return

        # Refactored Chrome Engine renaming/patching
        engine_exe = context.dist_dir / "pytron" / "engines" / "chrome" / "electron.exe"
        target_name = f"{context.out_name}.exe"
        renamed_exe = engine_exe.parent / target_name

        if engine_exe.exists():
            log(f"Patching engine binary: {target_name}", style="dim")
            if renamed_exe.exists():
                os.remove(renamed_exe)
            os.rename(engine_exe, renamed_exe)

            # Apply metadata to the renamed electron binary
            editor = MetadataEditor(package_dir=context.package_dir)
            editor.update(renamed_exe, context.app_icon, context.settings)


class MetadataModule(BuildModule):
    def post_build(self, context: BuildContext):
        log("Applying application metadata...", style="dim")
        main_exe_name = (
            f"{context.out_name}.exe" if sys.platform == "win32" else context.out_name
        )
        main_exe = context.dist_dir / main_exe_name

        if main_exe.exists():
            editor = MetadataEditor(package_dir=context.package_dir)
            editor.update(
                main_exe, context.app_icon, context.settings, dist_dir=context.dist_dir
            )


class InstallerModule(BuildModule):
    def post_build(self, context: BuildContext):
        if not getattr(context, "build_installer", False):
            return

        log("Building NSIS installer...", style="info")
        context.progress.update(
            context.task_id, description="Building Installer...", completed=90
        )

        from .installers import build_installer

        ret_code = build_installer(
            context.out_name, context.script_dir, context.app_icon
        )

        if ret_code != 0:
            log("Installer build failed.", style="error")


class PluginModule(BuildModule):
    def prepare(self, context: BuildContext):
        from ..plugin import discover_plugins

        plugins_dir = context.script_dir / "plugins"
        if not plugins_dir.exists():
            return

        # Automatically bundle the plugins directory
        log(f"Bundling plugins directory: {plugins_dir.name}", style="dim")
        context.add_data.append(f"{plugins_dir}{os.pathsep}plugins")

        log("Evaluating plugins for packaging hooks...", style="dim")
        plugin_objs = discover_plugins(str(plugins_dir))

        # Robust mock app for hook context
        class MockObject:
            def __call__(self, *args, **kwargs):
                return self

            def __iter__(self):
                return iter([])

            def __bool__(self):
                return False

            def __getattr__(self, name):
                return self

            def __getitem__(self, key):
                return self

            def __len__(self):
                return 0

            def to_dict(self):
                return {}

        class PackageAppMock:
            def __init__(self, settings_data, folder):
                self.config = settings_data
                self.app_root = folder
                self.storage_path = str(folder / "build" / "storage")
                self.logger = log
                self.state = MockObject()

            def __getattr__(self, name):
                return MockObject()

            def expose(self, *args, **kwargs):
                pass

            def broadcast(self, *args, **kwargs):
                pass

            def publish(self, *args, **kwargs):
                pass

            def on_exit(self, func):
                return func

        mock_app = PackageAppMock(context.settings, context.script_dir)

        # Build context for plugins to modify
        package_context = {
            "add_data": context.add_data,
            "hidden_imports": context.hidden_imports,
            "binaries": context.binaries,
            "extra_args": context.extra_args,
            "script": context.script,
            "out_name": context.out_name,
            "settings": context.settings,
            "package_dir": context.package_dir,
            "app_icon": context.app_icon,
        }

        for p in plugin_objs:
            try:
                # 1. Load Plugin for Hooks
                p.load(mock_app)
                p.invoke_package_hook(package_context)

                # 2. Auto-Harvest Dependencies (Crucial for Frozen Apps)
                # Since plugin code is loaded dynamically, PyInstaller won't see its imports.
                # We must explicitly tell it to bundle the declared dependencies.
                deps = p.python_dependencies
                if deps:
                    log(
                        f"  + Auto-injecting dependencies for {p.name}: {deps}",
                        style="dim",
                    )
                    package_context["hidden_imports"].extend(deps)

            except Exception as e:
                log(
                    f"Warning: Build analysis for plugin '{p.name}' failed: {e}",
                    style="warning",
                )

        # Sync back modified values
        context.out_name = package_context["out_name"]
        context.app_icon = package_context["app_icon"]
        context.settings = package_context["settings"]
        log(f"Build context updated by plugins", style="dim")


class HookModule(BuildModule):
    def prepare(self, context: BuildContext):
        if not (
            getattr(context, "collect_all", False)
            or getattr(context, "force_hooks", False)
        ):
            return

        from .pipeline import log
        from ..commands.harvest import generate_nuclear_hooks
        from ..commands.helpers import get_python_executable, get_venv_site_packages

        log("Generating nuclear build hooks...", style="info")
        temp_hooks_dir = context.build_dir / "nuclear_hooks"
        temp_hooks_dir.mkdir(parents=True, exist_ok=True)

        python_exe = get_python_executable()
        site_packages = get_venv_site_packages(python_exe)

        collect_mode = getattr(context, "collect_all", False)

        generate_nuclear_hooks(
            temp_hooks_dir,
            collect_all_mode=collect_mode,
            search_path=site_packages,
        )

        # PyInstaller expects hook paths. We'll pass it via extra_args or a dedicated field.
        # For now, let's add it to extra_args for PyInstaller.
        context.extra_args.append(f"--additional-hooks-dir={temp_hooks_dir}")
        log(f"Added nuclear hooks dir: {temp_hooks_dir}", style="dim")


class IconModule(BuildModule):
    """
    Handles icon resolution and high-quality conversion.
    Ensures that PNGs are converted to multi-size high-res ICO/ICNS.
    """

    def prepare(self, context: BuildContext):
        icon_path = context.app_icon

        # 1. Fallback to settings if not provided in CLI
        if not icon_path:
            config_icon = context.settings.get("icon")
            if config_icon:
                possible = context.script_dir / config_icon
                if possible.exists():
                    icon_path = str(possible)

        # 2. Hard fallback to Pytron default
        if not icon_path:
            pytron_icon = context.package_dir / "pytron" / "installer" / "pytron.ico"
            if pytron_icon.exists():
                icon_path = str(pytron_icon)

        if not icon_path or not os.path.exists(icon_path):
            log(
                "Warning: No app icon found. Using generic executable icon.",
                style="warning",
            )
            return

        icon_path = Path(icon_path)

        # 3. High-Res Conversion & Platform Specifics
        if icon_path.suffix.lower() == ".png":
            try:
                from PIL import Image

                log(f"Processing high-resolution icon: {icon_path.name}", style="dim")
                img = Image.open(icon_path)

                # --- Windows (ICO) ---
                if (
                    sys.platform == "win32" or True
                ):  # Generate ICO as a general fallback
                    ico_dir = context.build_dir / "icons"
                    ico_dir.mkdir(parents=True, exist_ok=True)
                    ico_path = ico_dir / f"{context.out_name}.ico"

                    sizes = [256, 128, 64, 48, 32, 16]
                    icon_images = []
                    resample = getattr(Image, "Resampling", Image).LANCZOS
                    for s in sizes:
                        if img.width >= s:
                            icon_images.append(img.resize((s, s), resample=resample))

                    if icon_images:
                        # Save with PNG compression for the 256px layer
                        icon_images[0].save(
                            ico_path,
                            format="ICO",
                            append_images=icon_images[1:],
                            bitmap_format=(
                                "png" if icon_images[0].width >= 256 else "bmp"
                            ),
                        )
                        if sys.platform == "win32":
                            context.app_icon = str(ico_path.resolve())

                # --- macOS (ICNS) ---
                if sys.platform == "darwin":
                    icns_path = ico_dir / f"{context.out_name}.icns"
                    try:
                        # Pillow supports ICNS saving
                        img.save(icns_path, format="ICNS")
                        context.app_icon = str(icns_path.resolve())
                        log(f"Generated high-res ICNS for macOS", style="dim")
                    except Exception as e:
                        log(f"Warning: ICNS conversion failed: {e}", style="warning")

                # --- Linux (PNG) ---
                if sys.platform == "linux":
                    # Just ensure we use the PNG directly
                    context.app_icon = str(icon_path.resolve())

            except ImportError:
                log(
                    "Warning: Pillow not installed. Icons may be low resolution.",
                    style="warning",
                )
                log(
                    "Install Pillow for high-res support: pip install Pillow",
                    style="warning",
                )
                context.app_icon = str(icon_path.resolve())
            except Exception as e:
                log(f"Warning: Icon processing failed: {e}", style="warning")
                context.app_icon = str(icon_path.resolve())
        else:
            # Already an ICO, ICNS, etc.
            context.app_icon = str(icon_path.resolve())

        # 4. Auto-include icon in bundle (so tray icons work)
        if context.app_icon and os.path.exists(context.app_icon):
            context.add_data.append(f"{context.app_icon}{os.pathsep}.")
