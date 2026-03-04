import os
import sys
import subprocess
import platform
import logging
import shutil

try:
    from ...exceptions import ForgeError
except ImportError:

    class ForgeError(Exception):
        pass


logger = logging.getLogger("Pytron.ServoForge")


class ServoForge:
    def __init__(self, target_dir=None):
        self.target_dir = target_dir or os.path.expanduser("~/.pytron/engines/servo")

    def provision(self):
        """Ensures the Servo engine (miniservo rust binary) is compiled and ready."""
        exe_name = "miniservo.exe" if platform.system() == "Windows" else "miniservo"
        exe_path = os.path.join(self.target_dir, exe_name)

        if not os.path.exists(exe_path):
            if not os.path.exists(self.target_dir):
                os.makedirs(self.target_dir, exist_ok=True)

            logger.info("Compiling the Servo Shell Rust implementation...")
            shell_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "shell")
            )

            # Using cargo build to compile the shell
            try:
                subprocess.run(
                    ["cargo", "build", "--release"],
                    cwd=shell_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Cargo build failed: {e.stderr}")
                raise ForgeError(f"Failed to compile Servo Shell: {e}")
            except FileNotFoundError:
                raise ForgeError(
                    "Cargo not found. Please install Rust toolchain to compile the Servo engine."
                )

            # Copy the binary to target_dir
            target_debug_exe = (
                "servo-shell.exe" if platform.system() == "Windows" else "servo-shell"
            )
            compiled_bin = os.path.join(
                shell_dir, "target", "release", target_debug_exe
            )

            if os.path.exists(compiled_bin):
                shutil.copy(compiled_bin, exe_path)
            else:
                raise ForgeError(f"Compiled binary not found at {compiled_bin}")

        return exe_path


def setup_engine(target_dir=None):
    forge = ServoForge(target_dir)
    return forge.provision()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_engine()
