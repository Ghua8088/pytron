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
from ..exceptions import ModuleError
from .installers import build_installer
from ..commands.helpers import get_python_executable, get_venv_site_packages
from ..commands.harvest import generate_nuclear_hooks

from .metadata import MetadataEditor
from .pipeline import BuildModule, BuildContext
from .utils import cleanup_dist


from .compilers import compile_script as cython_compile

# Legacy compatibility if needed or removed entirely
# def cython_compile(script_path: Path, build_dir: Path): ...


class SecurityModule(BuildModule):
    def __init__(self):
        self.original_script = None
        self.build_dir = Path("build") / "secure_build"
        self.compiled_pyd = None

    def prepare(self, context: BuildContext):
        log(
            "Shield: Initializing Secure Packaging (Static Linking)...",
            style="info",
        )

        # 1. SETUP BUILD DIR
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)

        # 2. GENERATE BOOTSTRAP SCRIPT
        bootstrap_path = self.build_dir / "bootstrap_env.py"
        bootstrap_content = """
import sys, os
import pytron

# 'app' is a built-in module linked statically into this executable.
try:
    import app 
except ImportError as e:
    print(f"Boot Error: Failed to load built-in app: {e}")
    sys.exit(1)

if __name__ == "__main__":
    pass
"""
        bootstrap_path.write_text(bootstrap_content)

        # 3. CONFIGURE SHIELDED ANALYSIS
        self.original_script = context.script
        context.script = bootstrap_path

        # Store original for PyInstaller module to pick up (Dual Analysis)
        context.original_script = self.original_script

        # Hide the original script and the 'app' module from PyInstaller
        # 'app' will be provided by the executable itself at runtime
        context.excludes.append(self.original_script.stem)
        context.excludes.append("app")

        # 4. FORCE NO-ARCHIVE (Required for our custom fusion process)
        if "--debug" not in context.extra_args:
            context.extra_args.extend(["--debug", "noarchive"])

    def compact_library(self, dist_path: Path, bundle_path: Path):
        """Fuses all loose .pyc files into a single safeguarded app.bundle,
        preserving the physical integrity of 'Special' packages (Native/Resource-heavy).
        """
        import zipfile

        internal_dir = dist_path / "_internal"

        if not internal_dir.exists():
            return

        log(
            f"Fusing Python library into {bundle_path.name} (Surgical Preservation)...",
            style="cyan",
        )

        # 1. DISCOVERY: Identify 'Special' packages that MUST stay loose
        preserving_packages = set()
        special_exts = (
            ".pyd",
            ".so",
            ".dll",
            ".lib",
            ".pem",
            ".onnx",
            ".prototxt",
            ".bin",
            ".pb",
        )

        for root, _, files in os.walk(internal_dir):
            if any(f.endswith(special_exts) for f in files):
                # Identify the top-level package name in _internal
                rel_parts = Path(root).relative_to(internal_dir).parts
                if rel_parts:
                    preserving_packages.add(rel_parts[0])

        log(
            f"  + Preserving physical package domains: {', '.join(preserving_packages)}",
            style="dim",
        )

        to_remove = []
        # USE ZIP_STORED for zero-latency imports
        with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_STORED) as bundle:
            # 2. Merge standard base_library
            base_zip = internal_dir / "base_library.zip"
            if base_zip.exists():
                with zipfile.ZipFile(base_zip, "r") as bzip:
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

        log(
            f"  + Shielded {len(to_remove)} modules into bundle. Logic is safeguarded.",
            style="dim",
        )

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
                log(
                    f"Warning: Could not clear {final_dist}. Some files may be locked.",
                    style="warning",
                )

        final_dist.mkdir(parents=True, exist_ok=True)

        log("Assembling secure distribution...", style="dim")
        for item in base_dist.iterdir():
            target = final_dist / item.name
            try:
                if item.is_dir():
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)
            except Exception as e:
                log(f"Warning: Could not copy {item.name}: {e}", style="warning")

        if sys.platform == "win32":
            # The compiled binary implicitly links to Python/VC DLLs.
            # They must be in the app root to be found by the Windows loader.
            internal_dir = final_dist / "_internal"
            if internal_dir.exists():
                for dll in internal_dir.glob("*.dll"):
                    name = dll.name.lower()
                    if (
                        name.startswith("python")
                        or name.startswith("vcruntime")
                        or name.startswith("msvcp")
                    ):
                        try:
                            shutil.copy2(dll, final_dist / dll.name)
                        except Exception as e:
                            pass

        # 5. FUSE AND CLOAK LIBRARY (Optional via --bundled)
        if getattr(context, "bundled", False):
            # Place the bundle inside _internal for a cleaner root
            bundle_path = final_dist / "_internal" / "app.bundle"
            self.compact_library(final_dist, bundle_path)
        else:
            log(
                "Skipping aggressive library bundling for stability (Safe Mode).",
                style="dim",
            )
            log("Use --bundled to group Python modules into app.bundle.", style="dim")

        # 7. COMPILE & LINK LOADER
        log("Compiling and Linking Static Loader...", style="info")

        # Determine static lib name
        lib_name = (
            "pytron_rust_bootloader.lib"
            if sys.platform == "win32"
            else "libpytron_rust_bootloader.a"
        )
        if (
            sys.platform == "win32"
            and not (
                context.package_dir
                / "pytron"
                / "pack"
                / "secure_loader"
                / "bin"
                / lib_name
            ).exists()
        ):
            # Check for alternate name
            if (
                context.package_dir
                / "pytron"
                / "pack"
                / "secure_loader"
                / "bin"
                / "libpytron_rust_bootloader.a"
            ).exists():
                lib_name = "libpytron_rust_bootloader.a"

        bootloader_lib = (
            context.package_dir / "pytron" / "pack" / "secure_loader" / "bin" / lib_name
        )

        if not bootloader_lib.exists():
            raise ModuleError(
                f"Static Bootloader not found at {bootloader_lib}. Please run 'pytron build-loader'.",
                module_name="SecurityModule",
            )

        # Compile app.c and link with bootloader_lib
        compiled_exe = cython_compile(
            self.original_script, self.build_dir, bootloader_lib
        )

        if not compiled_exe or not compiled_exe.exists():
            raise ModuleError(
                "Failed to compile fused executable.", module_name="SecurityModule"
            )

        final_loader = (
            final_dist / f"{original_out_name}.exe"
            if sys.platform == "win32"
            else final_dist / original_out_name
        )

        if final_loader.exists():
            os.remove(final_loader)

        shutil.copy2(compiled_exe, final_loader)

        log(f"  + Generated Fused Executable: {final_loader.name}", style="success")

        # Cleanup dummy base exe if it exists
        ext_exe = ".exe" if sys.platform == "win32" else ""
        base_exe = final_dist / f"{original_out_name}_base{ext_exe}"
        if base_exe.exists():
            try:
                os.remove(base_exe)
            except Exception:
                pass

        # 8. FINAL OPTIMIZATION
        cleanup_dist(final_dist)

        # Try to remove the temp base dist if possible
        try:
            shutil.rmtree(base_dist, ignore_errors=True)
        except Exception:
            pass

        return 0


def get_native_engine_libs():
    from .utils import get_native_engine_binaries

    return get_native_engine_binaries()


from .utils import cleanup_dist as prune_junk_folders


def apply_metadata_to_binary(
    binary_path, icon_path, settings, dist_dir, package_dir=None
):
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
    log(
        "Secure Build started via legacy entry point. Using SecurityModule internally.",
        style="info",
    )
    # For now, we'll let the pipeline handle it as the preferred route.
    return 0
