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


import hashlib


def _compute_spec_hash(context: BuildContext, makespec_cmd: list) -> str:
    """Computes a SHA-256 fingerprint of the makespec arguments, manifests, and environment packages."""
    h = hashlib.sha256()
    h.update(" ".join(makespec_cmd).encode("utf-8"))

    # Include dependency & project configuration manifests if present
    for manifest_name in [
        "requirements.json",
        "requirements.txt",
        "pyproject.toml",
        "settings.json",
    ]:
        manifest_path = context.script_dir / manifest_name
        if manifest_path.exists():
            try:
                h.update(manifest_path.read_bytes())
            except Exception:
                pass

    # Include virtual environment package fingerprint (.dist-info / .egg-info names)
    try:
        from ..commands.helpers import get_python_executable, get_venv_site_packages

        py_exe = get_python_executable()
        site_paths = get_venv_site_packages(py_exe)
        if isinstance(site_paths, (str, Path)):
            site_paths = [site_paths]
        for sp in site_paths:
            sp_str = str(sp)
            if sp_str and os.path.exists(sp_str) and os.path.isdir(sp_str):
                pkg_names = sorted(
                    [
                        name
                        for name in os.listdir(sp_str)
                        if name.endswith((".dist-info", ".egg-info"))
                    ]
                )
                h.update(",".join(pkg_names).encode("utf-8"))
    except Exception:
        pass

    return h.hexdigest()


def run_pyinstaller_build(context: BuildContext):
    """
    Core PyInstaller compiler stage.
    """
    try:
        # 1. Resolve Platform-Specific Libs
        from .utils import get_native_engine_binaries

        binaries = get_native_engine_binaries()
        dll_dest = os.path.join("pytron", "dependencies")

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

        if context.settings.get("console"):
            makespec_cmd.append("--console")
        else:
            makespec_cmd.append("--noconsole")

        # Add Core Native Engine Binaries
        for bin_name in binaries:
            bin_src = context.package_dir / "pytron" / "dependencies" / bin_name
            if bin_src.exists():
                makespec_cmd.append(f"--add-binary={bin_src}{os.pathsep}{dll_dest}")

        # Add Scripts
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

        # Force Package (Collect All from Settings)
        forced_pkgs = context.settings.get("force-package", [])
        if forced_pkgs:
            for pkg in forced_pkgs:
                makespec_cmd.append(f"--collect-all={pkg}")
            log(f"Forcing collect-all for packages: {forced_pkgs}", style="dim")

        makespec_cmd.extend(context.extra_args)

        if context.app_icon:
            makespec_cmd.extend(["--icon", context.app_icon])

        # Splash Screen
        splash_image = context.settings.get("splash_image")
        if splash_image:
            splash_path = context.script_dir / splash_image
            if splash_path.exists():
                makespec_cmd.extend(["--splash", str(splash_path)])
                log(f"Splash screen enabled: {splash_image}", style="dim")
            else:
                log(
                    f"Warning: Splash image not found at {splash_path}", style="warning"
                )

        # Spec Cache Check
        spec_file = Path(f"{context.out_name}.spec")
        spec_hash = _compute_spec_hash(context, makespec_cmd)

        context.build_dir.mkdir(parents=True, exist_ok=True)
        hash_file = context.build_dir / f"{context.out_name}.spec.hash"

        force_fresh = (
            context.settings.get("force_makespec", False)
            or "--clean" in context.extra_args
        )

        reuse_spec = False
        if spec_file.exists() and hash_file.exists() and not force_fresh:
            try:
                cached_hash = hash_file.read_text(encoding="utf-8").strip()
                if cached_hash == spec_hash:
                    reuse_spec = True
            except Exception:
                pass

        if reuse_spec:
            log(
                f"Reusing existing spec file {spec_file.name} (configuration unchanged)",
                style="info",
            )
            context.progress.update(
                context.task_id, description="Reusing Spec...", completed=35
            )
        else:
            log("Generating spec file...", style="info")
            context.progress.update(
                context.task_id, description="Generating Spec...", completed=30
            )
            log(f"Running makespec: {' '.join(makespec_cmd)}", style="dim")
            makespec_ret = run_command_with_output(makespec_cmd, style="dim")
            if makespec_ret != 0:
                return 1

            if not spec_file.exists():
                log(f"Error: spec file {spec_file} not found", style="error")
                return 1

            try:
                hash_file.write_text(spec_hash, encoding="utf-8")
            except Exception:
                pass

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
        ]
        # Only add --clean when not reusing cached spec
        if not reuse_spec:
            build_cmd.append("--clean")

        build_cmd.append(str(spec_file))

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
