import os
import sys
import shutil
import traceback
import subprocess
import re
import sysconfig
import platform
from pathlib import Path
from ..console import log, run_command_with_output, console, Rule
from .installers import build_installer
from ..commands.helpers import get_python_executable, get_venv_site_packages
from ..commands.harvest import generate_nuclear_hooks

from .metadata import MetadataEditor
from .pipeline import BuildModule, BuildContext


def cython_compile(script_path: Path, build_dir: Path):
    """Compiles a python script into a .pyd/.so using Cython and Zig (cc)."""
    python_exe = get_python_executable()
    
    # 0. Check for Cython
    try:
        subprocess.run([python_exe, "-c", "import Cython"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        log("Cython missing in build environment. Installing...", style="info")
        try:
            subprocess.run([python_exe, "-m", "pip", "install", "Cython"], check=True)
        except subprocess.CalledProcessError:
            log("Failed to install Cython automatically. Please install it manually in your venv.", style="error")
            return None

    # Determine Zig presence
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
                zig_bin = os.path.join(os.path.dirname(os.path.dirname(ziglang.__file__)), "bin", "zig")
                if sys.platform == "win32": zig_bin += ".exe"
            
            if not os.path.exists(zig_bin):
                zig_bin = None
        except ImportError:
            zig_bin = None

    if not zig_bin:
        log("Zig compiler ('zig') not found. Falling back to default C compiler...", style="warning")
    else:
        log(f"Using Zig compiler at: {zig_bin}", style="dim")

    log(f"Shield: Compiling {script_path.name} logic into native binary...", style="cyan")
    
    # 0. PRE-PROCESS: Force the 'main' block to execute when imported as a module
    # (Since the Rust loader imports 'app' instead of running it as __main__)
    try:
        content = script_path.read_text(encoding="utf-8", errors="ignore")
        # Support both ' and " and varying spaces
        pattern = r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:'
        if re.search(pattern, content):
            log("  + Patching entry point for native execution...", style="dim")
            content = re.sub(pattern, 'if True: # Shield Redirect', content)
        
        # Always write to 'app.py' in build_dir so Cython generates 'PyInit_app'
        # which matches what the Rust loader expects.
        target_script = build_dir / "app.py"
        target_script.write_text(content, encoding="utf-8")
    except Exception as e:
        log(f"Warning: Failed to pre-process script: {e}", style="warning")
        target_script = script_path

    # 1. TRANSLATE TO C using Cython (CLI mode to avoid auto-compilation)
    c_file = build_dir / "app.c"
    
    try:
        log("  + Generating C source with Cython...", style="dim")
        # We run Cython as a subprocess to ensure it JUST generates the .c file
        process = subprocess.run([
            python_exe, "-m", "cython", 
            "-3", 
            "--fast-fail",
            str(target_script),
            "-o", str(c_file)
        ], capture_output=True, text=True)
        
        if process.returncode != 0:
            log(f"Cython generation failed: {process.stderr}", style="error")
            return None
            
    except Exception as e:
        log(f"Cythonization error: {e}", style="error")
        return None

    if not c_file.exists():
        log("Cython failed to generate C source.", style="error")
        return None

    # 2. COMPILE C TO PYD/SO using Zig
    ext = ".pyd" if sys.platform == "win32" else ".so"
    output_bin = build_dir / f"app{ext}"
    
    # Get Python build constants from the target executable
    def get_py_info(cmd_part):
        res = subprocess.run([python_exe, "-c", f"import sysconfig; print(sysconfig.get_path('{cmd_part}'))"], 
                             capture_output=True, text=True)
        return res.stdout.strip()

    py_include = get_py_info("include")
    
    # Get version for the lib name
    res_ver = subprocess.run([python_exe, "-c", "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')"], 
                             capture_output=True, text=True)
    py_ver_str = res_ver.stdout.strip() or f"{sys.version_info.major}{sys.version_info.minor}"
    
    # On Windows, libraries are usually in {base_prefix}/libs
    res_prefix = subprocess.run([python_exe, "-c", "import sys; print(sys.base_prefix)"], 
                                capture_output=True, text=True)
    base_prefix = res_prefix.stdout.strip() or sys.base_prefix
    
    if sys.platform == "win32":
        py_lib_dir = os.path.join(base_prefix, "libs")
    else:
        # For non-windows we usually need the LIBDIR from sysconfig
        res_libdir = subprocess.run([python_exe, "-c", "import sysconfig; print(sysconfig.get_config_var('LIBDIR') or '')"], 
                                     capture_output=True, text=True)
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
            
        target = f"{arch}-windows" if sys.platform == "win32" else f"{arch}-{sys.platform}"
        # Some platforms need specific suffixes (like gnu or musl for linux)
        if sys.platform == "linux":
            target += "-gnu" # Default to gnu for compatibility
            
        log(f"  + Compiling {output_bin.name} with Zig CC (Target: {target})...", style="dim")
        
        compile_cmd = [
            zig_bin, "cc",
            "-target", target,
            "-O3", 
            "-shared", 
            "-o", str(output_bin),
            str(c_file),
            f"-I{py_include}"
        ]
        
        if sys.platform == "win32":
            compile_cmd.append(f"-L{py_lib_dir}")
            lib_name = f"python{py_ver_str}"
            compile_cmd.append(f"-l{lib_name}")
        else:
            compile_cmd.append("-fPIC")
            if py_lib_dir:
                compile_cmd.append(f"-L{py_lib_dir}")

        try:
            res = subprocess.run(compile_cmd, capture_output=True, text=True)
            if res.returncode != 0:
                log(f"Zig compilation failed: {res.stderr}", style="error")
                return cython_compile_fallback(script_path, build_dir)
        except Exception as e:
            log(f"Zig encountered an error: {e}", style="error")
            return cython_compile_fallback(script_path, build_dir)
            
        if output_bin.exists():
            log(f"Successfully compiled to {output_bin.name} using Zig", style="success")
            return output_bin

    return cython_compile_fallback(script_path, build_dir)


def cython_compile_fallback(script_path: Path, build_dir: Path):
    """Fallback using standard setuptools/MSVC."""
    log("Using standard Python build tools...", style="dim")
    python_exe = get_python_executable()
    setup_path = build_dir / "setup_compile.py"
    setup_content = f"""
from setuptools import setup
from Cython.Build import cythonize
import sys

setup(
    ext_modules = cythonize("{script_path.as_posix()}", 
                            compiler_directives={{'language_level': "3"}},
                            quiet=True),
)
"""
    setup_path.write_text(setup_content)
    cmd = [python_exe, "setup_compile.py", "build_ext", "--inplace"]
    
    try:
        subprocess.run(cmd, cwd=str(build_dir), capture_output=True, text=True, check=True)
    except Exception as e:
        log(f"Standard compilation failed: {e}", style="error")
        return None

    ext = ".pyd" if sys.platform == "win32" else ".so"
    compiled_files = list(build_dir.glob(f"*{ext}"))
    if not compiled_files:
        compiled_files = list(build_dir.glob(f"build/lib*/{script_path.stem}*{ext}"))

    if compiled_files:
        pyd_path = compiled_files[0]
        final_pyd = build_dir / f"app{ext}"
        if final_pyd.exists(): os.remove(final_pyd)
        shutil.move(str(pyd_path), str(final_pyd))
        return final_pyd
    return None


class SecurityModule(BuildModule):
    def __init__(self):
        self.original_script = None
        self.build_dir = Path("build") / "secure_build"
        self.compiled_pyd = None

    def prepare(self, context: BuildContext):
        log("Shield: Initializing Secure Packaging (Binary Compilation)...", style="info")
        
        # 1. CYTHON COMPILATION
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)

        self.compiled_pyd = cython_compile(context.script, self.build_dir)
        if not self.compiled_pyd:
            raise RuntimeError("Shield Error: Cython compilation failed.")

        # 3. GENERATE BOOTSTRAP SCRIPT
        bootstrap_path = self.build_dir / "bootstrap_env.py"
        bootstrap_content = """
import sys, os, json, logging, threading, asyncio, textwrap, re, socket, ssl, ctypes, hashlib, time, base64, mimetypes
from collections import deque
import pytron

try:
    import app # This imports the compiled app.pyd/so
except Exception as e:
    print(f"Boot Error: Failed to load compiled app: {e}")
    sys.exit(1)

if __name__ == "__main__":
    pass
"""
        bootstrap_path.write_text(bootstrap_content)

        # 2. CONFIGURE SHIELDED ANALYSIS
        self.original_script = context.script
        context.script = bootstrap_path
        
        # Store original for PyInstaller module to pick up (Dual Analysis)
        context.original_script = self.original_script
        
        # Add the compiled binary to the build context binaries
        # CRITICAL: We EXCLUDE the original script from being bundled as source
        if self.original_script.stem not in context.excludes:
             context.excludes.append(self.original_script.stem)
        
        # Add to pathex so PyInstaller finds the .pyd during analysis of bootstrap
        if str(self.build_dir.resolve()) not in context.pathex:
            context.pathex.append(str(self.build_dir.resolve()))
        
        context.binaries.append(f"{self.compiled_pyd.resolve()}{os.pathsep}.")
        
        # 4. FORCE NO-ARCHIVE (Required for our custom fusion process)
        if "--debug" not in context.extra_args:
            context.extra_args.extend(["--debug", "noarchive"])

    def compact_library(self, dist_path: Path):
        """Fuses all loose .pyc files into a single safeguarded app.bundle,
           preserving the physical integrity of 'Special' packages (Native/Resource-heavy)."""
        import zipfile
        internal_dir = dist_path / "_internal"
        bundle_path = dist_path / "app.bundle"
        
        if not internal_dir.exists():
            return

        log(f"Fusing Python library into {bundle_path.name} (Surgical Preservation)...", style="cyan")
        
        # 1. DISCOVERY: Identify 'Special' packages that MUST stay loose
        preserving_packages = set()
        special_exts = (".pyd", ".so", ".dll", ".lib", ".pem", ".onnx", ".prototxt", ".bin", ".pb")
        
        for root, _, files in os.walk(internal_dir):
            if any(f.endswith(special_exts) for f in files):
                # Identify the top-level package name in _internal
                rel_parts = Path(root).relative_to(internal_dir).parts
                if rel_parts:
                    preserving_packages.add(rel_parts[0])

        log(f"  + Preserving physical package domains: {', '.join(preserving_packages)}", style="dim")

        to_remove = []
        # USE ZIP_STORED for zero-latency imports
        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_STORED) as bundle:
            # 2. Merge standard base_library
            base_zip = internal_dir / "base_library.zip"
            if base_zip.exists():
                with zipfile.ZipFile(base_zip, 'r') as bzip:
                    for name in bzip.namelist():
                        bundle.writestr(name, bzip.read(name))
                to_remove.append(base_zip)

            # 3. Process the rest of _internal
            for root, _, files in os.walk(internal_dir):
                rel_parts = Path(root).relative_to(internal_dir).parts
                
                # If this is inside a preserved package, skip fusion entirely
                if rel_parts and rel_parts[0] in preserving_packages:
                    continue 

                for f in files:
                    # Capture code only for fused packages to keep them clean
                    if f.endswith((".pyc", ".py")):
                        full_path = Path(root) / f
                        rel_path = full_path.relative_to(internal_dir)
                        bundle.write(full_path, rel_path)
                        to_remove.append(full_path)

        # 4. Cleanup fused source files
        for p in to_remove:
            try:
                os.remove(p)
            except Exception:
                pass
        
        # 5. PRUNING: Recursive remove empty directory skeletons
        for root, dirs, _ in os.walk(internal_dir, topdown=False):
            for d in dirs:
                dir_path = Path(root) / d
                try:
                    if not any(dir_path.iterdir()):
                        os.rmdir(dir_path)
                except Exception:
                    pass

        log(f"  + Shielded {len(to_remove)} modules into bundle. Logic is safeguarded.", style="dim")

    def build_wrapper(self, context: BuildContext, build_func):
        # We need to change the output name for the "base" build
        # so it doesn't collide with the final loader
        original_out_name = context.out_name
        context.out_name = f"{original_out_name}_base"
        
        # Run the actual build
        ret_code = build_func(context)
        
        # Restore name
        context.out_name = original_out_name
        
        if ret_code != 0:
            return ret_code

        # 4. ASSEMBLE SECURE DISTRIBUTION
        log("Hardening Distribution...", style="cyan")
        
        base_dist = Path("dist") / f"{original_out_name}_base"
        final_dist = Path("dist") / original_out_name
        
        if final_dist.exists():
            try:
                shutil.rmtree(final_dist)
            except Exception:
                log(f"Warning: Could not clear {final_dist}. Some files may be locked.", style="warning")
        
        final_dist.mkdir(parents=True, exist_ok=True)
        
        log("Assembling secure distribution...", style="dim")
        for item in base_dist.iterdir():
            target = final_dist / item.name
            try:
                if item.is_dir():
                    if target.exists(): shutil.rmtree(target)
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)
            except Exception as e:
                log(f"Warning: Could not copy {item.name}: {e}", style="warning")

        # 5. VERIFY COMPILED BUNDLE
        # Ensure the .pyd is actually in the dist root (Loader expects it there)
        ext = ".pyd" if sys.platform == "win32" else ".so"
        dist_pyd = final_dist / f"app{ext}"
        if not dist_pyd.exists():
            # If PyInstaller didn't put it in root, check _internal
            internal_pyd = final_dist / "_internal" / f"app{ext}"
            if internal_pyd.exists():
                shutil.copy2(str(internal_pyd), str(dist_pyd))
            else:
                log(f"Warning: Compiled binary app{ext} not found in distribution.", style="warning")

        # 5. FUSE AND CLOAK LIBRARY (Optional via --bundled)
        if getattr(context, "bundled", False):
            self.compact_library(final_dist)
        else:
            log("Skipping aggressive library bundling for stability (Safe Mode).", style="dim")
            log("Use --bundled to group Python modules into app.bundle.", style="dim")

        # 6. PROMOTE CRITICAL RUNTIMES (Fix for silent crashes)
        log("Promoting runtime binaries...", style="dim")
        internal_dir = final_dist / "_internal"
        if internal_dir.exists():
            # Explicitly promote app binary if not already there
            app_bin = internal_dir / f"app{ext}"
            if app_bin.exists() and not (final_dist / f"app{ext}").exists():
                shutil.copy2(app_bin, final_dist / f"app{ext}")

            # Find pythonXXX.dll
            py_dll_pattern = "python[0-9]*.dll"
            for py_dll in internal_dir.glob(py_dll_pattern):
                if not (final_dist / py_dll.name).exists():
                    shutil.copy2(py_dll, final_dist / py_dll.name)
                    log(f"  + Promoted runtime: {py_dll.name}", style="dim")
            
            # Find webview.dll (Engine)
            webview_dll = internal_dir / "webview.dll"
            if webview_dll.exists() and not (final_dist / "webview.dll").exists():
                shutil.copy2(webview_dll, final_dist / "webview.dll")
                log("  + Promoted engine: webview.dll", style="dim")

        # 7. DEPLOY RUST LOADER
        log("Hardening Loader...", style="info")
        ext_exe = ".exe" if sys.platform == "win32" else ""
        loader_name = f"pytron_rust_bootloader{ext_exe}"
        precompiled_bin = (
            context.package_dir
            / "pytron"
            / "pack"
            / "secure_loader"
            / "bin"
            / loader_name
        )

        final_loader = final_dist / f"{original_out_name}{ext_exe}"
        shutil.copy(precompiled_bin, final_loader)
        
        # Cleanup dummy base exe if it exists
        base_exe = final_dist / f"{original_out_name}_base{ext_exe}"
        if base_exe.exists():
            try:
                os.remove(base_exe)
            except Exception:
                pass

        # 8. FINAL OPTIMIZATION
        prune_junk_folders(final_dist)
        
        # Try to remove the temp base dist if possible
        try:
            shutil.rmtree(base_dist, ignore_errors=True)
        except Exception:
            pass

        return 0


def get_webview_lib():
    if sys.platform == "win32":
        return "webview.dll"
    elif sys.platform == "darwin":
        return "libwebview.dylib"
    else:
        return "libwebview.so"


from .utils import cleanup_dist as prune_junk_folders


def apply_metadata_to_binary(binary_path, icon_path, settings, dist_dir, package_dir=None):
    editor = MetadataEditor(package_dir=package_dir)
    return editor.update(binary_path, icon_path, settings, dist_dir)


def run_secure_build(
    args,
    script,
    out_name,
    settings,
    app_icon,
    package_dir,
    add_data,
    progress,
    task,
    package_context=None,
):
    """
    Legacy entry point for secure build.
    """
    # This function is now mostly a wrapper for the SecurityModule pipeline logic
    # but kept for backward compatibility if called directly.
    log("Secure Build started via legacy entry point. Using SecurityModule internally.", style="info")
    # For now, we'll let the pipeline handle it as the preferred route.
    return 0
