import os
import sys
import shutil
import subprocess  # nosec B404
import platform
from pathlib import Path
from ..console import log, run_command_with_output, console, Rule
from ..commands.helpers import get_python_executable, get_venv_site_packages
from .installers import build_installer


from .pipeline import BuildContext


def run_nuitka_build(context: BuildContext):
    """
    Core Nuitka compiler stage.
    """
    log("Packaging using Nuitka (Native Compilation)...", style="info")

    # 1. Check for Nuitka
    python_exe = get_python_executable()

    # Try importing nuitka or checking executable
    nuitka_missing = True
    try:
        res = subprocess.run([python_exe, "-c", "import nuitka"], capture_output=True)
        if res.returncode == 0:
            nuitka_missing = False
    except Exception as e:
        log(
            f"Unable to verify Nuitka via interpreter import check: {e}. "
            "Falling back to executable detection.",
            style="warning",
        )

    if nuitka_missing and shutil.which("nuitka"):
        nuitka_missing = False

    if nuitka_missing:
        log(
            "Nuitka is required for compilation but not found. Auto-installing 'pytron[nuitka]'...",
            style="warning",
        )
        try:
            subprocess.check_call(
                [python_exe, "-m", "pip", "install", "nuitka", "zstandard"]
            )
            log("Successfully installed Nuitka toolchain!", style="success")
        except subprocess.CalledProcessError as e:
            log(f"Failed to auto-install Nuitka: {e}", style="error")
            raise SystemExit(1)

    # 2. Build Nuitka Command
    cmd = [
        python_exe,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--output-dir=dist",
    ]

    if context.is_onefile:
        cmd.append("--onefile")
        ext = ".exe" if sys.platform == "win32" else ".bin"
        cmd.append(f"--output-filename={context.out_name}{ext}")

    # Metadata
    title = context.settings.get("title") or context.out_name
    version = context.settings.get("version", "1.0.0")
    author = context.settings.get("author") or "Pytron User"

    cmd.extend(
        [
            f"--company-name={author}",
            f"--product-name={title}",
            f"--file-version={version}",
            f"--product-version={version}",
        ]
    )

    if context.app_icon:
        if sys.platform == "win32":
            cmd.append(f"--windows-icon-from-ico={context.app_icon}")
        elif sys.platform == "linux":
            cmd.append(f"--linux-icon={context.app_icon}")

    if context.settings.get("console"):
        if sys.platform == "win32":
            cmd.append("--windows-console-mode=force")
    else:
        if sys.platform == "win32":
            cmd.append("--windows-console-mode=disable")

    # Assets
    # Native Engine Binaries
    from .utils import get_native_engine_binaries

    binaries = get_native_engine_binaries()

    for bin_name in binaries:
        bin_src = context.package_dir / "pytron" / "dependencies" / bin_name
        if bin_src.exists():
            cmd.append(f"--include-data-file={bin_src}=pytron/dependencies/{bin_name}")

    for item in context.add_data:
        if os.pathsep in item:
            src, dst = item.split(os.pathsep, 1)
            if os.path.isdir(src):
                cmd.append(f"--include-data-dir={src}={dst}")
            else:
                if dst == ".":
                    dst = os.path.basename(src)
                cmd.append(f"--include-data-file={src}={dst}")

    # Hidden Imports
    for imp in context.hidden_imports:
        cmd.append(f"--include-module={imp}")

    cmd.extend(context.extra_args)

    cmd.append(str(context.script))

    log(f"Running Nuitka: {' '.join(cmd)}", style="dim")
    ret_code = run_command_with_output(cmd, style="dim")

    return ret_code
