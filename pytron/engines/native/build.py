import subprocess
import shutil
import os
import sys

# Paths
# This script is in pytron/pytron/engines/native/
ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
# ROOT is d:\playground\pytron (3 levels up)
ROOT = os.path.abspath(os.path.join(ENGINE_DIR, "..", "..", ".."))

# Destination Directory (Python runtime dependencies)
DEPENDENCIES_DIR = os.path.join(ROOT, "pytron", "dependencies")

# Check for Android Target
is_android = "--android" in sys.argv

# Determine Extension (Python Extension Module)
if is_android:
    LIB_NAME = "libpytron_native.so"
    EXT_NAME = "libpytron-native.so"  # Android loader expects hyphen
    TARGET_SUBDIR = os.path.join("aarch64-linux-android", "release")
    DEPENDENCIES_DIR = os.path.join(DEPENDENCIES_DIR, "android", "arm64-v8a")
elif sys.platform == "win32":
    LIB_NAME = "pytron_native.dll"  # Cargo outputs .dll on Windows
    EXT_NAME = "pytron_native.pyd"  # Python expects .pyd
    TARGET_SUBDIR = "release"
elif sys.platform == "darwin":
    LIB_NAME = "libpytron_native.dylib"
    EXT_NAME = "pytron_native.so"  # Python on Mac expects .so
    TARGET_SUBDIR = "release"
else:
    LIB_NAME = "libpytron_native.so"
    EXT_NAME = "pytron_native.so"
    TARGET_SUBDIR = "release"

TARGET_PATH = os.path.join(ENGINE_DIR, "target", TARGET_SUBDIR, LIB_NAME)
DEST_PATH = os.path.join(DEPENDENCIES_DIR, EXT_NAME)


def build():
    print(f"\n[BUILD] Starting Iron Engine Build...")
    print(f"   Target OS: {'Android (arm64)' if is_android else 'Host System'}")
    print(f"   Source: {ENGINE_DIR}")
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

    cargo_cmd = ["cargo", "rustc", "--release"]

    if is_android:
        # Cross-compilation for Android
        cargo_cmd.extend(["--target", "aarch64-linux-android"])
        print("[INFO] Target: aarch64-linux-android")

        # We need to ensure the linker is set. If the user has a .cargo/config.toml, great.
        # Otherwise, we might need to point to a zig-cc wrapper or NDK.
        # If the rust_linker.bat exists from builder.py, we can attempt to use it.
        linker_path = os.path.join(
            ROOT,
            "pytron",
            "platforms",
            "android",
            "tools",
            "zig",
            "wrappers",
            "rust_linker.bat",
        )
        if os.path.exists(linker_path):
            env["CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER"] = linker_path
            print(f"[INFO] Using Zig-Linker: {linker_path}")

    # Apply safe linker flags for symbol collision prevention
    try:
        # Append sys.path to find build_utils in the root's pytron dir
        sys.path.append(os.path.join(ROOT))
        from pytron.build_utils import get_safe_linker_flags

        safe_flags = get_safe_linker_flags(
            "pytron_native", os.path.join(ENGINE_DIR, "build")
        )

        if safe_flags:
            cargo_cmd.append("--")
            cargo_cmd.extend(safe_flags)
            print(f"[INFO] Applying Shield Linker Flags: {' '.join(safe_flags)}")
    except Exception as e:
        print(f"[WARNING] Could not apply symbol shield: {e}")

    # --- macOS: tell pyo3's build script which Python interpreter to use ---
    # Setting PYO3_PYTHON is sufficient. pyo3's `extension-module` feature
    # automatically emits `-undefined dynamic_lookup` on macOS so all _Py*
    # symbols resolve at runtime from the embedding interpreter.
    # Do NOT add manual -l or RUSTFLAGS: macOS framework Python's LDLIBRARY
    # is a path ("Python.framework/Versions/3.11/Python"), not a valid -l name.
    if sys.platform == "darwin" and not is_android:
        env["PYO3_PYTHON"] = sys.executable
        print(f"[INFO] macOS: PYO3_PYTHON set to {sys.executable}")


    try:
        subprocess.check_call(cargo_cmd, cwd=ENGINE_DIR, env=env)
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
        print("[INFO] You are ready to run Pytron with Native Power.")
    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")
        try:
            if os.path.exists(DEST_PATH):
                os.remove(DEST_PATH)  # Force delete
            shutil.copy2(TARGET_PATH, DEST_PATH)
            print(f"[SUCCESS] Deployed to: {DEST_PATH} (Force Overwrite)")
        except Exception as e2:
            print(f"[ERROR] Force copy failed: {e2}. Is the app running?")
            sys.exit(1)


if __name__ == "__main__":
    build()
