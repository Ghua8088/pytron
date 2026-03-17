import subprocess
import shutil
import os
import sys

# Paths
# This script is in pytron/pytron/platforms/pytron_os/
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
# ROOT is d:\playground\pytron (3 levels up)
ROOT = os.path.abspath(os.path.join(MODULE_DIR, "..", "..", ".."))

# Destination Directory (Python runtime dependencies)
DEPENDENCIES_DIR = os.path.join(ROOT, "pytron", "dependencies")

# Determine Extension (Python Extension Module)
if sys.platform == "win32":
    LIB_NAME = "pytron_os.dll"  # Cargo outputs .dll on Windows
    EXT_NAME = "pytron_os.pyd"  # Python expects .pyd
    TARGET_SUBDIR = "release"
elif sys.platform == "darwin":
    LIB_NAME = "libpytron_os.dylib"
    EXT_NAME = "pytron_os.so"  # Python on Mac expects .so
    TARGET_SUBDIR = "release"
else:
    LIB_NAME = "libpytron_os.so"
    EXT_NAME = "pytron_os.so"
    TARGET_SUBDIR = "release"

TARGET_PATH = os.path.join(MODULE_DIR, "target", TARGET_SUBDIR, LIB_NAME)
DEST_PATH = os.path.join(DEPENDENCIES_DIR, EXT_NAME)


def build():
    print(f"\n[BUILD] Starting Pytron OS Module Build...")
    print(f"   Target OS: Host System")
    print(f"   Source: {MODULE_DIR}")
    print(f"   Target: {DEST_PATH}\n")

    # 1. Check Rust
    try:
        subprocess.check_output(["cargo", "--version"])
    except FileNotFoundError:
        print("[ERROR] Rust (cargo) is not installed or not in PATH.")
        sys.exit(1)

    # 2. Build Release
    print(f"[INFO] Compiling (Release Mode)... This may take a minute.")
    env = os.environ.copy()
    env["PYO3_USE_ABI3_FORWARD_COMPATIBILITY"] = "1"

    cargo_cmd = ["cargo", "rustc", "--release", "--manifest-path", "Cargo.toml"]

    # Apply safe linker flags for symbol collision prevention
    try:
        # Append sys.path to find build_utils in the root's pytron dir
        sys.path.append(os.path.join(ROOT))
        from pytron.build_utils import get_safe_linker_flags

        safe_flags = get_safe_linker_flags(
            "pytron_os", os.path.join(MODULE_DIR, "build")
        )
        
        if safe_flags:
            cargo_cmd.append("--")
            cargo_cmd.extend(safe_flags)
            print(f"[INFO] Applying Shield Linker Flags: {' '.join(safe_flags)}")
    except Exception as e:
        print(f"[WARNING] Could not apply symbol shield: {e}")

    try:
        subprocess.check_call(cargo_cmd, cwd=MODULE_DIR, env=env)
    except subprocess.CalledProcessError:
        print("\n[ERROR] Cargo Build Failed! Check the error messages above.")
        sys.exit(1)

    # 3. Verify Artifact
    if not os.path.exists(TARGET_PATH):
        print(f"\n[ERROR] Build finished but artifact not found at:\n   {TARGET_PATH}")
        sys.exit(1)

    # 4. Deploy
    print(f"\n[SUCCESS] Build Successful!")
    print(f"[INFO] Copying artifact to dependencies...")

    os.makedirs(DEPENDENCIES_DIR, exist_ok=True)

    try:
        shutil.copy2(TARGET_PATH, DEST_PATH)
        print(f"[SUCCESS] Deployed to: {DEST_PATH}")
    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")
        try:
            if os.path.exists(DEST_PATH):
                os.remove(DEST_PATH)  # Force delete
            shutil.copy2(TARGET_PATH, DEST_PATH)
            print(f"[SUCCESS] Deployed to: {DEST_PATH} (Force Overwrite)")
        except Exception as e2:
            print(
                f"[ERROR] Force copy failed: {e2}. Is the app using this module right now?"
            )
            sys.exit(1)


if __name__ == "__main__":
    build()
