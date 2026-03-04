import os
import sys
import shutil
import subprocess
import platform
import re
from pathlib import Path
from ..console import log


def get_python_executable():
    """Returns the path to the current python executable."""
    return sys.executable


def ensure_cython(python_exe):
    """Ensures Cython is installed/available."""
    try:
        subprocess.run(
            [python_exe, "-c", "import Cython"], check=True, capture_output=True
        )
    except subprocess.CalledProcessError:
        log("Cython missing in build environment. Installing...", style="info")
        try:
            subprocess.run([python_exe, "-m", "pip", "install", "Cython"], check=True)
        except subprocess.CalledProcessError:
            log(
                "Failed to install Cython automatically. Please install it manually in your venv.",
                style="error",
            )
            return False
    return True


def find_zig():
    """Locates the Zig compiler binary."""
    zig_bin = shutil.which("zig")
    if not zig_bin:
        # Check if ziglang package is installed and use its binary
        try:
            import ziglang

            zig_bin = os.path.join(os.path.dirname(ziglang.__file__), "bin", "zig")
            if sys.platform == "win32":
                zig_bin += ".exe"
            if not os.path.exists(zig_bin):
                # Try sibling bin directory for some installations
                zig_bin = os.path.join(
                    os.path.dirname(os.path.dirname(ziglang.__file__)), "bin", "zig"
                )
                if sys.platform == "win32":
                    zig_bin += ".exe"

            if not os.path.exists(zig_bin):
                zig_bin = None
        except ImportError:
            zig_bin = None

    if not zig_bin:
        log(
            "Zig compiler ('zig') not found. Secure compilation requires Zig (https://ziglang.org).",
            style="error",
        )
    else:
        log(f"Using Zig compiler at: {zig_bin}", style="dim")

    return zig_bin


def cython_gen_c(script_path: Path, build_dir: Path, python_exe: str):
    """Generates a C file from a Python script using Cython."""
    # 0. PRE-PROCESS: Force the 'main' block to execute when imported as a module
    try:
        content = script_path.read_text(encoding="utf-8", errors="ignore")
        pattern = r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:'
        if re.search(pattern, content):
            log("  + Patching entry point for native execution...", style="dim")
            content = re.sub(pattern, "if True: # Shield Redirect", content)

        target_script = build_dir / "app.py"
        target_script.write_text(content, encoding="utf-8")
    except Exception as e:
        log(f"Warning: Failed to pre-process script: {e}", style="warning")
        target_script = script_path

    c_file = build_dir / "app.c"

    try:
        log("  + Generating C source with Cython...", style="dim")
        process = subprocess.run(
            [
                python_exe,
                "-m",
                "cython",
                "-3",
                "--fast-fail",
                str(target_script),
                "-o",
                str(c_file),
            ],
            capture_output=True,
            text=True,
        )

        if process.returncode != 0:
            log(f"Cython generation failed: {process.stderr}", style="error")
            return None
    except Exception as e:
        log(f"Cythonization error: {e}", style="error")
        return None

    if not c_file.exists():
        log("Cython failed to generate C source.", style="error")
        return None

    # Patch for MSVC/Rust compatibility:
    # 1. Define _fltused for floating point support
    # 2. Provide WinMain wrapper to satisfy GUI subsystem requirements while using main()
    try:
        with open(c_file, "a") as f:
            f.write("\n\n/* Pytron Compatibility Hack */\n")
            f.write("#ifdef _WIN32\n")
            f.write("#include <windows.h>\n")
            f.write("extern int main(int argc, char **argv);\n")
            f.write("int _fltused = 0;\n")
            f.write(
                "int WINAPI WinMain(HINSTANCE hI, HINSTANCE hP, LPSTR lp, int nS) {\n"
            )
            f.write("    return main(__argc, __argv);\n")
            f.write("}\n")
            f.write("#endif\n")
    except Exception as e:
        log(f"Warning: Failed to append compatibility patch: {e}", style="warning")

    return c_file


def compile_c_to_executable(
    c_file: Path, build_dir: Path, zig_bin: str, python_exe: str, bootloader_lib: Path
):
    """Compiles C source + Static Bootloader + Python Lib into a single executable."""
    ext = ".exe" if sys.platform == "win32" else ""
    output_bin = build_dir / f"app{ext}"

    # Get Python build constants
    res_include = subprocess.run(
        [python_exe, "-c", "import sysconfig; print(sysconfig.get_path('include'))"],
        capture_output=True,
        text=True,
    )
    py_include = res_include.stdout.strip()

    res_ver = subprocess.run(
        [
            python_exe,
            "-c",
            "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')",
        ],
        capture_output=True,
        text=True,
    )
    py_ver_str = (
        res_ver.stdout.strip() or f"{sys.version_info.major}{sys.version_info.minor}"
    )

    res_prefix = subprocess.run(
        [python_exe, "-c", "import sys; print(sys.base_prefix)"],
        capture_output=True,
        text=True,
    )
    base_prefix = res_prefix.stdout.strip() or sys.base_prefix

    if sys.platform == "win32":
        py_lib_dir = os.path.join(base_prefix, "libs")
    else:
        res_libdir = subprocess.run(
            [
                python_exe,
                "-c",
                "import sysconfig; print(sysconfig.get_config_var('LIBDIR') or '')",
            ],
            capture_output=True,
            text=True,
        )
        py_lib_dir = res_libdir.stdout.strip() or os.path.join(base_prefix, "lib")

    if zig_bin:
        # Determine target architecture
        machine = platform.machine().lower()
        if machine in ["amd64", "x86_64"]:
            arch = "x86_64"
        elif machine in ["arm64", "aarch64"]:
            arch = "aarch64"
        else:
            arch = "x86"

        target = (
            f"{arch}-windows-gnu"
            if sys.platform == "win32"
            else f"{arch}-{sys.platform}-gnu"
        )

        log(
            f"  + Compiling {output_bin.name} (Static Link) with Zig (Target: {target})...",
            style="dim",
        )

        compile_cmd = [
            zig_bin,
            "build-exe",
            str(c_file),
            str(bootloader_lib),
            "-target",
            target,
            "-O",
            "ReleaseFast",
            f"-femit-bin={output_bin}",
            f"-I{py_include}",
            "-lc",
        ]

        if sys.platform == "win32":
            compile_cmd.extend(["--subsystem", "windows"])
            compile_cmd.append(f"-L{py_lib_dir}")
            compile_cmd.append(f"-L{bootloader_lib.parent}")
            lib_name = f"python{py_ver_str}"
            compile_cmd.append(f"-l{lib_name}")
            # System libs required by Rust/Python
            compile_cmd.extend(
                [
                    "-lws2_32",
                    "-luserenv",
                    "-lbcrypt",
                    "-ladvapi32",
                    "-lntdll",
                    "-lkernel32",
                    "-luser32",
                    "-lole32",
                    "-lshell32",
                    "-lshlwapi",
                ]
            )
        else:
            # Linux
            if py_lib_dir:
                compile_cmd.append(f"-L{py_lib_dir}")

            # Python standard link
            compile_cmd.append(
                f"-lpython{sys.version_info.major}.{sys.version_info.minor}"
            )
            # System libs
            compile_cmd.extend(["-lpthread", "-ldl", "-lutil", "-lm"])

        try:
            res = subprocess.run(compile_cmd, capture_output=True, text=True)
            if res.returncode != 0:
                log(f"Zig compilation failed: {res.stderr}", style="error")
                return None
        except Exception as e:
            log(f"Zig encountered an error: {e}", style="error")
            return None

        if output_bin.exists():
            log(
                f"Successfully compiled fused executable: {output_bin.name}",
                style="success",
            )
            return output_bin

    return None


def compile_script(script_path: Path, build_dir: Path, bootloader_lib: Path):
    """Orchestrates the full compilation pipeline using Zig."""
    python_exe = get_python_executable()

    if not ensure_cython(python_exe):
        return None

    zig_bin = find_zig()
    if not zig_bin:
        return None

    c_file = cython_gen_c(script_path, build_dir, python_exe)
    if not c_file:
        return None

    # Strict Zig Compilation
    return compile_c_to_executable(
        c_file, build_dir, zig_bin, python_exe, bootloader_lib
    )
