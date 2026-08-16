import logging
import os
import platform
import shutil
import stat
import sys
import zipfile

import requests

from ...exceptions import ForgeError

logger = logging.getLogger("Pytron.ChromeForge")

# Configuration
ELECTRON_VERSION = "30.0.6"  # Stable version used for the Mojo Bridge


def _runtime_keep_files():
    if sys.platform == "win32":
        return [
            "electron.exe",
            "resources.pak",
            "chrome_100_percent.pak",
            "chrome_200_percent.pak",
            "icudtl.dat",
            "v8_context_snapshot.bin",
            "snapshot_blob.bin",
            "ffmpeg.dll",
            "libEGL.dll",
            "libGLESv2.dll",
            "vk_swiftshader_icd.json",
            "vk_swiftshader.dll",
            "vulkan-1.dll",
            "d3dcompiler_47.dll",
        ]

    if sys.platform == "darwin":
        return [
            "Electron.app",
        ]

    return [
        "electron",
        "chrome-sandbox",
        "chrome_crashpad_handler",
        "resources.pak",
        "chrome_100_percent.pak",
        "chrome_200_percent.pak",
        "icudtl.dat",
        "v8_context_snapshot.bin",
        "snapshot_blob.bin",
        "libffmpeg.so",
        "libEGL.so",
        "libGLESv2.so",
        "vk_swiftshader_icd.json",
    ]


def _runtime_keep_dirs():
    keep = ["locales", "resources"]
    if sys.platform.startswith("linux"):
        keep.append("swiftshader")
    return keep


def _required_runtime_files():
    if sys.platform == "win32":
        return ["electron.exe", "ffmpeg.dll", "resources.pak"]
    if sys.platform == "darwin":
        return ["Electron.app"]
    return ["electron", "libffmpeg.so", "resources.pak"]


def get_electron_url():
    system = sys.platform  # 'win32', 'darwin', or 'linux'

    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        arch = "arm64"
    elif machine in ("armv7l", "armv6l"):
        arch = "armv7l"
    else:
        arch = "x64"

    if system == "win32":
        return f"https://github.com/electron/electron/releases/download/v{ELECTRON_VERSION}/electron-v{ELECTRON_VERSION}-win32-{arch}.zip"
    elif system == "darwin":
        return f"https://github.com/electron/electron/releases/download/v{ELECTRON_VERSION}/electron-v{ELECTRON_VERSION}-darwin-{arch}.zip"
    else:
        return f"https://github.com/electron/electron/releases/download/v{ELECTRON_VERSION}/electron-v{ELECTRON_VERSION}-linux-{arch}.zip"


def download_electron(dest_path):
    url = get_electron_url()
    logger.info(
        f"Connecting to Chrome Shell Depository (Electron v{ELECTRON_VERSION})..."
    )

    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
    except Exception as e:
        raise ForgeError(f"Failed to download Chrome Engine core from {url}: {e}")

    total_size = int(response.headers.get("content-length", 0))
    temp_zip = os.path.join(dest_path, "electron.zip")

    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TransferSpeedColumn,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task(
                "[cyan]Injecting Chromium Core...", total=total_size
            )

            with open(temp_zip, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))

        logger.info("Extraction phase: Unpacking Mojo shells...")
        with zipfile.ZipFile(temp_zip, "r") as zip_ref:
            zip_ref.extractall(dest_path)
    except Exception as e:
        raise ForgeError(f"Failed to unpack Chrome Engine core: {e}")
    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)


def perform_surgery(path):
    """Strips the Electron binary down to a minimal Chrome Shell."""
    logger.info("Performing binary surgery (removing bloat)...")

    to_keep = _runtime_keep_files()
    keep_dirs = _runtime_keep_dirs()

    try:
        # 1. Clean root
        for item in os.listdir(path):
            if item not in to_keep and item not in keep_dirs:
                p = os.path.join(path, item)
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)

        # 2. Clean locales (Keep only en-US)
        locales_path = os.path.join(path, "locales")
        if os.path.exists(locales_path):
            for locale in os.listdir(locales_path):
                if locale != "en-US.pak":
                    os.remove(os.path.join(locales_path, locale))

        # 3. Inject Shell Logic
        logger.info("Injecting Mojo Bridge logic...")
        app_path = os.path.join(path, "resources", "app")
        if not os.path.exists(app_path):
            os.makedirs(app_path)

        # Source the shell files from our core
        core_shell_src = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "shell")
        )
        for file in os.listdir(core_shell_src):
            shutil.copy(
                os.path.join(core_shell_src, file), os.path.join(app_path, file)
            )
    except Exception as e:
        raise ForgeError(f"Binary surgery failed: {e}")


class ChromeForge:
    def __init__(self, target_dir=None):
        self.target_dir = target_dir or os.path.expanduser("~/.pytron/engines/chrome")

    def _is_runtime_intact(self):
        for name in _required_runtime_files():
            if not os.path.exists(os.path.join(self.target_dir, name)):
                return False
        return True

    def _reset_target_dir(self):
        if os.path.exists(self.target_dir):
            shutil.rmtree(self.target_dir, ignore_errors=True)
        os.makedirs(self.target_dir, exist_ok=True)

    def provision(self):
        """Ensures the Chrome engine is installed and ready."""
        exe_name = "electron.exe" if sys.platform == "win32" else "electron"
        exe_path = os.path.join(self.target_dir, exe_name)

        if not os.path.exists(exe_path) or not self._is_runtime_intact():
            self._reset_target_dir()

            download_electron(self.target_dir)
            perform_surgery(self.target_dir)

        if sys.platform != "win32" and os.path.exists(exe_path):
            try:
                current_mode = os.stat(exe_path).st_mode
                os.chmod(
                    exe_path,
                    current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
                )
            except Exception as e:
                logger.warning(f"Failed to mark Chrome shell executable: {e}")

            for helper in ["chrome-sandbox", "chrome_crashpad_handler"]:
                helper_path = os.path.join(self.target_dir, helper)
                if os.path.exists(helper_path):
                    try:
                        helper_mode = os.stat(helper_path).st_mode
                        os.chmod(
                            helper_path,
                            helper_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to mark Chrome helper executable ({helper}): {e}"
                        )

        return exe_path


def setup_engine(target_dir=None):
    forge = ChromeForge(target_dir)
    return forge.provision()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_engine()
