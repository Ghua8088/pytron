import os
import shutil
import subprocess
import sys
from pathlib import Path


def build_and_deploy():
    """
    Compiles the Rust bootloader and deploys the binary to the bin/ folder.
    This ensures the 'secure' packager always has the latest hardened version.
    """
    # 1. Setup paths
    base_dir = Path(__file__).parent.resolve()
    bin_dir = base_dir / "bin"
    target_dir = base_dir / "target" / "release"

    # 2. Determine static library name
    lib_names = []
    if sys.platform == "win32":
        lib_names = ["pytron_rust_bootloader.lib", "libpytron_rust_bootloader.a"]
    else:
        lib_names = ["libpytron_rust_bootloader.a"]

    # 3. Compile Rust (Release mode)
    print("[*] Starting build of static bootloader...")
    env = os.environ.copy()

    # macOS requires special linker flags for PyO3
    if sys.platform == "darwin":
        rustflags = env.get("RUSTFLAGS", "")
        # Add dynamic lookup for Python symbols
        env["RUSTFLAGS"] = (
            f"{rustflags} -C link-arg=-undefined -C link-arg=dynamic_lookup".strip()
        )
        print("[INFO] Applying macOS Linker Flags (dynamic_lookup)")
    elif sys.platform.startswith("linux"):
        rustflags = env.get("RUSTFLAGS", "")
        env["RUSTFLAGS"] = (
            f"{rustflags} -C link-arg=-Wl,--unresolved-symbols=ignore-all".strip()
        )
        print("[INFO] Applying Linux Linker Flags (ignore-all)")

    try:
        cargo_bin = shutil.which("cargo") or "cargo"
        subprocess.run(
            [cargo_bin, "build", "--release"], cwd=str(base_dir), check=True, env=env
        )  # nosec B603
    except FileNotFoundError:
        print("[!] Error: 'cargo' not found. Please install Rust (https://rustup.rs).")
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("[!] Error: Cargo build failed.")
        sys.exit(1)

    # 4. Ensure bin directory exists
    bin_dir.mkdir(exist_ok=True)

    # 5. Move static lib to bin/
    found_lib = None
    for name in lib_names:
        candidate = target_dir / name
        if candidate.exists():
            found_lib = candidate
            break

    # Also check .deps or native directory if not found in root release? No, usually in release.

    if found_lib and found_lib.exists():
        dest_lib = bin_dir / found_lib.name
        shutil.copy2(found_lib, dest_lib)
        print(
            f"[+] Success: Deployed static library {found_lib.name} to {bin_dir.name}/"
        )
    else:
        print(f"[!] Error: Could not find compiled static library in {target_dir}")
        print(f"    Expected one of: {lib_names}")
        sys.exit(1)


if __name__ == "__main__":
    build_and_deploy()
