import os
import sys
import subprocess  # nosec B404
import platform
from pathlib import Path
from ..console import log, run_command_with_output, console, Rule
from ..commands.helpers import get_python_executable, get_venv_site_packages
from ..commands.harvest import generate_nuclear_hooks
from .installers import build_installer
from .utils import cleanup_dist

from .metadata import MetadataEditor
from .pipeline import BuildContext


def run_pyinstaller_build(context: BuildContext):
    """
    Core PyInstaller compiler stage.
    """
    try:
        log("Generating spec file...", style="info")
        context.progress.update(
            context.task_id, description="Generating Spec...", completed=30
        )

        # 1. Resolve Platform-Specific Libs
        dll_name = "webview.dll"
        if sys.platform == "linux":
            dll_name = "libwebview.so"
        elif sys.platform == "darwin":
            dll_name = (
                "libwebview_arm64.dylib"
                if platform.machine() == "arm64"
                else "libwebview_x64.dylib"
            )

        dll_src = context.package_dir / "pytron" / "dependancies" / dll_name
        dll_dest = os.path.join("pytron", "dependancies")

        # 2. Build Makespec Command
        makespec_cmd = [
            get_python_executable(),
            "-m",
            "PyInstaller.utils.cliutils.makespec",
            "--name",
            context.out_name,
        ]

        if context.is_onefile:
            makespec_cmd.append("--onefile")
        else:
            makespec_cmd.append("--onedir")

        # Console handling
        # Note: We'd ideally have this in the context, but for now we read from context.settings/args if available
        # In this refactor, we'll assume context has what it needs.
        # For simplicity, if --console was passed to CLI, we should have it in extra_args or similar.
        # But let's check settings for now.
        if context.settings.get("console"):
            makespec_cmd.append("--console")
        else:
            makespec_cmd.append("--noconsole")

        # Add Core Webview DLL
        makespec_cmd.append(f"--add-binary={dll_src}{os.pathsep}{dll_dest}")

        # Add Scripts
        # For secure builds, we add BOTH the bootstrap and the original script
        # PyInstaller will analyze both for dependencies, but bootstrap (first)
        # stays as the primary entry point script.
        makespec_cmd.append(str(context.script))

        if context.is_secure and hasattr(context, "original_script"):
            makespec_cmd.append(str(context.original_script))

        # Add Runtime Hooks
        if sys.platform == "win32":
            utf8_hook = context.package_dir / "pytron" / "utf8_hook.py"
            if utf8_hook.exists():
                makespec_cmd.append(f"--runtime-hook={utf8_hook}")

        for hook in context.runtime_hooks:
            makespec_cmd.append(f"--runtime-hook={hook}")

        # Add Assets (from Modules)
        for item in context.add_data:
            makespec_cmd.extend(["--add-data", item])

        for item in context.binaries:
            makespec_cmd.extend(["--add-binary", item])

        for imp in context.hidden_imports:
            makespec_cmd.append(f"--hidden-import={imp}")

        for ex in context.excludes:
            makespec_cmd.append(f"--exclude-module={ex}")

        for p in context.pathex:
            makespec_cmd.append(f"--paths={p}")

        makespec_cmd.extend(context.extra_args)

        if context.app_icon:
            makespec_cmd.extend(["--icon", context.app_icon])

        # Run Makespec
        log(f"Running makespec: {' '.join(makespec_cmd)}", style="dim")
        makespec_ret = run_command_with_output(makespec_cmd, style="dim")
        if makespec_ret != 0:
            return 1

        spec_file = Path(f"{context.out_name}.spec")
        if not spec_file.exists():
            log(f"Error: spec file {spec_file} not found", style="error")
            return 1

        # Fortress / Spec Optimization Hook
        if (
            context.settings.get("optimize_spec")
            or context.is_secure
            or hasattr(context, "fortress_active")
        ):
            try:
                from fortress import SpecOptimizer

                optimizer = SpecOptimizer(spec_file)
                optimizer.optimize()
                log("Fortress: Spec optimization applied.", style="dim")
            except ImportError:
                pass
            except Exception as e:
                log(f"Warning: Spec optimization failed: {e}", style="warning")

        # 3. Execution Phase
        build_cmd = [
            get_python_executable(),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(spec_file),
        ]

        context.progress.update(
            context.task_id, description="Compiling...", completed=50
        )
        log(f"Building from Spec: {' '.join(build_cmd)}", style="dim")

        ret_code = run_command_with_output(build_cmd, style="dim")

        if ret_code == 0:
            # Cleanup
            has_splash = bool(context.settings.get("splash_image"))
            cleanup_dist(Path("dist") / context.out_name, preserve_tk=has_splash)

        return ret_code

    except Exception as e:
        log(f"PyInstaller build failed: {e}", style="error")
        return 1
