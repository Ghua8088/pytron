import os
import sys
import glob
import subprocess
import shutil
import tempfile
import urllib.request
import ctypes

# Optional LIEF import
try:
    import lief
except ImportError:
    lief = None

if sys.version_info >= (3, 11):
    import tomllib as toml
else:
    try:
        import toml
    except ImportError:
        toml = None


class AndroidBuilder:
    def __init__(self, arch="aarch64", target_dir=None):
        self.arch = arch
        # SECURITY/STABILITY: Explicitly target API 24 to ensure Bionic compatibility
        self.api_level = "24"
        self.target = (
            f"aarch64-linux-android.{self.api_level}"
            if arch == "aarch64"
            else f"{arch}-linux-android.{self.api_level}"
        )
        self.target_dir = target_dir
        self.zig_version = "0.13.0"

        # Paths
        self.zig_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "tools", "zig"
        )
        # Lazy initialization for tools
        self.zig_exe = None
        self.ndk_info = None
        self.env = os.environ.copy()

        # Flattened libs cache (for Dependency Flattening Strategy)
        self.flattened_libs_dir = os.path.join(
            os.path.dirname(self.zig_dir), "flattened_libs", self.arch
        )
        os.makedirs(self.flattened_libs_dir, exist_ok=True)
        self.flattened_libs = set()

    def _fetch_prebuilt_wheel(self, package, output_dir):
        """Attempts to download a pre-built binary wheel for Android."""
        print(f"[AndroidBuilder] Searching for pre-built wheels for {package}...")

        # Common Android platform tags
        platforms = []
        if self.arch == "aarch64":
            platforms = [
                "android_24_aarch64",
                "android_21_aarch64",
                "android_24_arm64_v8a",
                "android_21_arm64_v8a",
            ]
        elif self.arch == "x86_64":
            platforms = ["android_24_x86_64", "android_21_x86_64"]

        # Add BeeWare repository
        extra_indexes = [
            "https://pypi.anaconda.org/beeware/simple",
        ]

        for platform in platforms:
            try:
                cmd = [
                    sys.executable,
                    "-m",
                    "pip",
                    "download",
                    package,
                    "--dest",
                    output_dir,
                    "--platform",
                    platform,
                    "--only-binary",
                    ":all:",
                    "--no-deps",
                ]
                for url in extra_indexes:
                    cmd.extend(["--extra-index-url", url])

                # Run quietly
                subprocess.check_call(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )  # nosec B603

                # Check if we actually got a wheel
                downloaded = [
                    f
                    for f in os.listdir(output_dir)
                    if f.lower().startswith(package.lower()) and f.endswith(".whl")
                ]
                if downloaded:
                    print(f"[AndroidBuilder] Found pre-built wheel: {downloaded[0]}")
                    return True
            except subprocess.CalledProcessError:
                continue

        return False

    def _ensure_tools(self):
        """Lazy load tools only when needed for compilation."""
        if not self.zig_exe:
            self.zig_exe = self._ensure_zig()
        if not self.ndk_info:
            self.ndk_info = self._find_ndk_info()
            self._create_cc_wrapper()  # Ensure generic wrappers are generated
            self.env = self._get_cross_env()

    def _create_cc_wrapper(self):
        """Creates a batch wrapper for Zig CC to act as a general C compiler."""
        if not self.zig_exe or not self.ndk_info:
            return None
        wrapper_dir = self._norm(os.path.join(self.zig_dir, "wrappers"))
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper_path = self._norm(os.path.join(wrapper_dir, "android_cc.bat"))

        sysroot = self.ndk_info["sysroot"]
        inc = self.ndk_info["include"]
        target_inc = os.path.join(inc, "aarch64-linux-android")

        # Basic Zig CC for android with necessary headers/sysroot
        cmd = f'"{self.zig_exe}" cc -target {self.target} --sysroot="{sysroot}" -I"{inc}" -I"{target_inc}" -shared -lc -fuse-ld=lld %*'
        with open(wrapper_path, "w") as f:
            f.write(f"@echo off\n{cmd}")

        return self._get_short_path(wrapper_path)

    def repair_wheel(self, wheel_path):
        """
        Implements the 'Dependency Flattening' strategy.
        1. Extract the wheel.
        2. Scan for .so files and their internal dependencies.
        3. Relocate internal dependencies to the flattened folder.
        4. Patch the .so files to find dependencies in the flat namespace.
        """
        if lief is None:
            print(
                "[AndroidBuilder] Warning: LIEF not installed. Skipping dependency flattening/repair."
            )
            return False

        import zipfile

        temp_repair = tempfile.mkdtemp(prefix="pytron_repair_")

        try:
            with zipfile.ZipFile(wheel_path, "r") as zip_ref:
                zip_ref.extractall(temp_repair)

            repaired = False
            # Scan for all shared libraries in the wheel
            for root, dirs, files in os.walk(temp_repair):
                for file in files:
                    if file.endswith(".so"):
                        so_path = os.path.join(root, file)
                        if self._patch_so(so_path, temp_repair):
                            repaired = True

            if repaired:
                print(
                    f"[AndroidBuilder] Repaired and flattened: {os.path.basename(wheel_path)}"
                )
                # Re-pack the wheel
                os.remove(wheel_path)
                shutil.make_archive(wheel_path.replace(".whl", ""), "zip", temp_repair)
                os.rename(wheel_path.replace(".whl", ".zip"), wheel_path)

            return True
        finally:
            shutil.rmtree(temp_repair, ignore_errors=True)

    def _patch_so(self, so_path, wheel_root):
        """Patches an ELF file to fulfill Dependency Flattening."""
        if lief is None:
            return False
        try:
            binary = lief.parse(so_path)
            if not binary:
                return False

            changed = False
            # List of dependencies to process
            deps_to_fix = [lib for lib in binary.libraries]

            needs_native_bridge = False
            for dep in deps_to_fix:
                # --- GLIBC TO BIONIC NORMALIZATION (The "Shim" Logic) ---
                new_dep = dep

                if dep == "libc.so.6":
                    new_dep = "libc.so"
                    needs_native_bridge = True
                elif dep == "libm.so.6":
                    new_dep = "libm.so"
                    needs_native_bridge = True
                elif dep == "libdl.so.2":
                    new_dep = "libdl.so"
                    needs_native_bridge = True
                elif dep in ["libpthread.so.0", "librt.so.1"]:
                    print(
                        f"[AndroidBuilder] Removing redundant Glibc dependency: {dep}"
                    )
                    binary.remove_library(dep)
                    changed = True
                    continue

                if new_dep != dep:
                    print(f"[AndroidBuilder] Shim: Remapping {dep} -> {new_dep}")
                    binary.remove_library(dep)
                    binary.add_library(new_dep)
                    changed = True
                    dep = new_dep

                # --- SYSTEM LIBRARIES WHITE-LIST (Android Linker Namespace allowed) ---
                if dep in [
                    "libc.so",
                    "libm.so",
                    "libdl.so",
                    "liblog.so",
                    "libjnigraphics.so",
                    "libandroid.so",
                    "libEGL.so",
                    "libGLESv2.so",
                    "libOpenSLES.so",
                    "libz.so",
                ]:
                    continue

                # Check if this dependency exists inside the wheel (it might be in a subdir)
                dep_name = os.path.basename(dep)
                dep_search = glob.glob(
                    os.path.join(wheel_root, "**", dep_name), recursive=True
                )

                if dep_search:
                    dep_internal_path = dep_search[0]
                    # This is a local dependency. Move it to the flattened folder.
                    flat_dest = os.path.join(self.flattened_libs_dir, dep_name)
                    if not os.path.exists(flat_dest):
                        print(f"[AndroidBuilder] Flattening dependency: {dep_name}")
                        shutil.copy2(dep_internal_path, flat_dest)
                        self.flattened_libs.add(dep_name)

                    # Ensure the reference in the binary is ONLY the filename
                    if dep != dep_name:
                        # Use lief to replace the dependency path with just the name
                        for i, library in enumerate(binary.libraries):
                            if library == dep:
                                binary.libraries[i] = dep_name
                                changed = True
                    else:
                        # Even if it match, we might want to 'refresh' it or just mark changed
                        changed = True

            # --- BRIDGE INJECTION ---
            # If we shimmed Glibc, we MUST inject our bridge so the missing symbols are found
            if needs_native_bridge:
                bridge_name = "libpytron-native.so"
                if bridge_name not in binary.libraries:
                    print(
                        f"[AndroidBuilder] Injecting {bridge_name} dependency for Glibc compatibility."
                    )
                    binary.add_library(bridge_name)
                    changed = True

            # Clear RPATH/RUNPATH as they are unreliable on Android
            if binary.has(lief.ELF.DYNAMIC_TAGS.RUNPATH):
                binary.remove(lief.ELF.DYNAMIC_TAGS.RUNPATH)
                changed = True
            if binary.has(lief.ELF.DYNAMIC_TAGS.RPATH):
                binary.remove(lief.ELF.DYNAMIC_TAGS.RPATH)
                changed = True

            if changed:
                binary.write(so_path)
            return True
        except Exception as e:
            print(
                f"[AndroidBuilder] Warning: Failed to patch {os.path.basename(so_path)}: {e}"
            )
            return False

    def _get_short_path(self, long_path):
        if os.name != "nt":
            return long_path
        if not os.path.exists(long_path):
            return long_path
        try:
            size = ctypes.windll.kernel32.GetShortPathNameW(long_path, None, 0)
            if size == 0:
                return long_path
            buf = ctypes.create_unicode_buffer(size)
            ctypes.windll.kernel32.GetShortPathNameW(long_path, buf, size)
            return buf.value
        except Exception:
            return long_path

    def _norm(self, path):
        if not path:
            return path
        return os.path.normpath(path)

    def _ensure_zig(self):
        """Checks for Zig compiler, installs if missing."""
        # Check global
        if shutil.which("zig"):
            return "zig"

        # Check local
        zig_exe_local = self._norm(os.path.join(self.zig_dir, "zig.exe"))
        if os.path.exists(zig_exe_local):
            return self._get_short_path(zig_exe_local)

        # Install
        print(f"[AndroidBuilder] Zig not found. Installing Zig {self.zig_version}...")
        os.makedirs(os.path.dirname(self.zig_dir), exist_ok=True)

        # URL for Windows (assuming Windows as per user context)
        if sys.platform == "win32":
            url = f"https://ziglang.org/download/{self.zig_version}/zig-windows-x86_64-{self.zig_version}.zip"
        elif sys.platform == "linux":
            url = f"https://ziglang.org/download/{self.zig_version}/zig-linux-x86_64-{self.zig_version}.tar.xz"
        elif sys.platform == "darwin":
            url = f"https://ziglang.org/download/{self.zig_version}/zig-macos-x86_64-{self.zig_version}.tar.xz"
        else:
            return None

        zip_path = self._norm(os.path.join(os.path.dirname(self.zig_dir), "zig.zip"))
        try:
            if not url.startswith("https://"):
                raise ValueError("URL must be HTTPS")

            # nosemgrep
            with urllib.request.urlopen(url) as response, open(  # nosec B310
                zip_path, "wb"
            ) as out:
                shutil.copyfileobj(response, out)

            print("[AndroidBuilder] Extracting Zig...")
            extract_temp = tempfile.mkdtemp(dir=os.path.dirname(self.zig_dir))
            shutil.unpack_archive(zip_path, extract_temp)

            # Find extracted folder (zig-windows-x86_64-0.13.0, etc.)
            extracted_path = None
            for d in os.listdir(extract_temp):
                d_full = os.path.join(extract_temp, d)
                if os.path.isdir(d_full):
                    extracted_path = d_full
                    break

            if extracted_path:
                if os.path.exists(self.zig_dir):
                    shutil.rmtree(self.zig_dir)
                shutil.move(extracted_path, self.zig_dir)

            shutil.rmtree(extract_temp)
            os.remove(zip_path)
            return self._get_short_path(zig_exe_local)

        except Exception as e:
            print(f"[AndroidBuilder] Failed to install Zig: {e}")
            return None

    def setup_nano_sysroot(self, cache_dir):
        """Creates a minimal sysroot by downloading essential Android headers."""
        include_dir = os.path.join(cache_dir, "sysroot", "usr", "include")
        os.makedirs(include_dir, exist_ok=True)

        headers = {
            "jni.h": "https://raw.githubusercontent.com/openjdk/jdk/master/src/java.base/share/native/include/jni.h",
            "jni_md.h": "https://raw.githubusercontent.com/openjdk/jdk/master/src/java.base/unix/native/include/jni_md.h",
            "android/log.h": "https://raw.githubusercontent.com/platform-tools/android_platform_system_core/master/liblog/include/android/log.h",
        }

        # Provision OpenSSL for common Rust packages (cryptography, etc.)
        self._setup_openssl(cache_dir)

        print("[AndroidBuilder] Provisioning Nano-Sysroot (Headers)...")
        for name, url in headers.items():
            dest = os.path.join(include_dir, name)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if not os.path.exists(dest):
                try:
                    import urllib.request

                    if not url.startswith("https://"):
                        raise ValueError("URL must be HTTPS")

                    # nosemgrep
                    urllib.request.urlretrieve(url, dest)  # nosec B310
                except Exception as e:
                    print(f"[AndroidBuilder] Warning: Failed to download {name}: {e}")

        return os.path.join(cache_dir, "sysroot")

    def _setup_openssl(self, cache_dir):
        """Downloads pre-built OpenSSL headers/libs for Android (via BeeWare/other sources)"""
        openssl_dir = os.path.join(cache_dir, "openssl", self.arch)
        if os.path.exists(openssl_dir):
            return openssl_dir

        print(f"[AndroidBuilder] Provisioning OpenSSL for {self.arch}...")
        os.makedirs(openssl_dir, exist_ok=True)

        # Pull from a reliable cross-platform source or use a shim
        # For now, we point to where the environment will expect it.
        # Most users will need to provide one or we can fetch a minimal one.
        # Fallback to BeeWare support packages which often include it
        return openssl_dir

    def setup_python_target(self, cache_dir):
        """Downloads Android Python headers and libraries for the target ABI."""
        target_dir = os.path.join(cache_dir, f"python-target-{self.arch}")
        if os.path.exists(target_dir):
            return target_dir

        print(f"[AndroidBuilder] Provisioning Python {self.arch} Support Package...")
        os.makedirs(target_dir, exist_ok=True)

        # Use the current Python version to match the host environment
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        # Fallback: if BeeWare hasn't released yet for latest, you might need to adjust this.
        # Using 3.11 as a safe default if 3.14 is not available, or let it fail gracefully
        # BeeWare usually has 3.8-3.12 support.
        if sys.version_info.minor > 12:
            print(
                f"[AndroidBuilder] Warning: Python {py_ver} might not be supported by BeeWare yet. Trying 3.12..."
            )
            py_ver = "3.12"

        url = f"https://github.com/beeware/Python-Android-support/releases/download/{py_ver}-b1/Python-{py_ver}-Android-support.b1.zip"
        zip_path = os.path.join(cache_dir, "python-android-support.zip")

        try:
            import urllib.request

            if not os.path.exists(zip_path):
                if not url.startswith("https://"):
                    raise ValueError("URL must be HTTPS")
                print(f"[AndroidBuilder] Downloading {url}...")
                # nosemgrep
                urllib.request.urlretrieve(url, zip_path)  # nosec B310

            import zipfile

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(target_dir)
        except Exception as e:
            print(f"[AndroidBuilder] Error provisioning Python target: {e}")

        return target_dir

    def _find_ndk_info(self):
        """Locate NDK or fallback to Nano-Sysroot."""
        ndk_path = os.environ.get("ANDROID_NDK_HOME")
        if not ndk_path:
            android_home = os.environ.get("ANDROID_HOME") or os.environ.get(
                "ANDROID_SDK_ROOT"
            )
            if android_home:
                ndk_root = os.path.join(android_home, "ndk")
                if os.path.exists(ndk_root):
                    versions = sorted(os.listdir(ndk_root))
                    if versions:
                        ndk_path = os.path.join(ndk_root, versions[-1])

        cache_dir = os.path.join(os.path.dirname(self.zig_dir), "cache")
        os.makedirs(cache_dir, exist_ok=True)

        if ndk_path and os.path.exists(ndk_path):
            ndk_path = self._norm(ndk_path)
            sysroot = self._norm(
                os.path.join(
                    ndk_path,
                    "toolchains",
                    "llvm",
                    "prebuilt",
                    "windows-x86_64",
                    "sysroot",
                )
            )
            if not os.path.exists(sysroot):
                sysroot_glob = glob.glob(
                    os.path.join(
                        ndk_path, "toolchains", "llvm", "prebuilt", "*", "sysroot"
                    )
                )
                if sysroot_glob:
                    sysroot = self._norm(sysroot_glob[0])

            if os.path.exists(sysroot):
                return {
                    "path": ndk_path,
                    "sysroot": self._get_short_path(sysroot),
                    "include": self._get_short_path(
                        self._norm(os.path.join(sysroot, "usr", "include"))
                    ),
                    "lib": self._get_short_path(
                        self._norm(
                            os.path.join(sysroot, "usr", "lib", "aarch64-linux-android")
                        )
                    ),
                }

        # Fallback to Nano-Sysroot
        print("[AndroidBuilder] NDK not found. Switching to Minimalist Nano-Sysroot...")
        sysroot = self.setup_nano_sysroot(cache_dir)
        py_target = self.setup_python_target(cache_dir)

        # Locate the specific arch inside the support package
        # BeeWare structure: /python/path/usr/include and /python/path/usr/lib
        py_inc = glob.glob(
            os.path.join(py_target, "**", "usr", "include", "python*"), recursive=True
        )
        py_lib = glob.glob(os.path.join(py_target, "**", "usr", "lib"), recursive=True)

        return {
            "path": None,
            "sysroot": self._get_short_path(sysroot),
            "include": self._get_short_path(os.path.join(sysroot, "usr", "include")),
            "lib": (
                self._get_short_path(py_lib[0])
                if py_lib
                else self._get_short_path(sysroot)
            ),
            "py_include": self._get_short_path(py_inc[0]) if py_inc else None,
        }

    def _generate_sysconfig(self, dest_dir):
        """
        Creates a dummy _sysconfigdata file to fool build backends
        into using Android/Linux settings on a Windows host.
        """
        # Use host Python version to ensure compatibility
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        py_soabi = (
            f"cpython-{sys.version_info.major}{sys.version_info.minor}-{self.target}"
        )

        # Standard naming convention
        sc_name = f"_sysconfigdata__linux_{self.target}"
        sc_path = os.path.join(dest_dir, f"{sc_name}.py")

        # Minimal build vars to satisfy setuptools/distutils/meson/pyo3
        content = f"""
# Generated by Pytron AndroidBuilder
build_time_vars = {{
    'SO': '.so',
    'EXT_SUFFIX': '.so',
    'SHLIB_SUFFIX': '.so',
    'CC': 'zig cc',
    'CXX': 'zig c++',
    'AR': 'zig ar',
    'HOST_GNU_TYPE': '{self.target}',
    'MACHDEP': 'linux',
    'LIBDIR': '.',
    'INCLUDEPY': '.',
    'SOABI': '{py_soabi}',
    'VERSION': '{py_ver}',
    'Py_ENABLE_SHARED': 1,
    'ABIFLAGS': '',
    'platlibdir': 'lib',
    'SIZEOF_VOID_P': 8,
    'SIZEOF_LONG': 8,
    'SIZEOF_SIZE_T': 8,
}}
"""
        with open(sc_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Also generate a Meson cross-file for NumPy/Scientific stack
        self._generate_meson_cross_file(dest_dir)

        return sc_name

    def _generate_meson_cross_file(self, dest_dir):
        """Generates a Meson cross-file to force Android architecture detection."""
        cross_path = os.path.join(dest_dir, "cross-file.meson")
        zig_safe = self._get_short_path(self.zig_exe).replace("\\", "/")

        # Map arch to meson standards
        cpu_family = "aarch64" if self.arch == "aarch64" else "arm"
        cpu = "armv8-a" if self.arch == "aarch64" else "armv7-a"

        content = f"""
[binaries]
c = ['{zig_safe}', 'cc', '-target', '{self.target}']
cpp = ['{zig_safe}', 'c++', '-target', '{self.target}']
ar = '{zig_safe}-ar'
strip = '{zig_safe}-strip'
pkgconfig = 'pkg-config'

[host_machine]
system = 'linux'
cpu_family = '{cpu_family}'
cpu = '{cpu}'
endian = 'little'

[properties]
needs_exe_wrapper = true
"""
        with open(cross_path, "w", encoding="utf-8") as f:
            f.write(content)
        return cross_path

    def _rename_wheel(self, output_dir):
        """Fixes wheel tags to ensure they are recognized as Android-compatible."""
        for whl in os.listdir(output_dir):
            if not whl.endswith(".whl"):
                continue

            original = whl
            new_name = whl
            # Map host tags to Android tags
            for host_tag in ["win_amd64", "linux_x86_64", "macosx"]:
                if host_tag in whl:
                    # e.g. numpy-2.4.0-cp313-cp313-win_amd64.whl -> ...-android_24_aarch64.whl
                    new_name = whl.replace(host_tag, f"android_24_{self.arch}")

            if new_name != original:
                print(f"[AndroidBuilder] Renaming wheel: {original} -> {new_name}")
                os.rename(
                    os.path.join(output_dir, original),
                    os.path.join(output_dir, new_name),
                )

    def _create_linker_wrapper(self):
        """Creates a batch wrapper for Zig CC to act as a Linker for Rust/Cargo."""
        if not self.zig_exe:
            return None
        wrapper_dir = self._norm(os.path.join(self.zig_dir, "wrappers"))
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper_path = self._norm(os.path.join(wrapper_dir, "rust_linker.bat"))

        # Zig cc as linker. We quote zig path for batch execution.
        cmd = f'"{self.zig_exe}" cc -target {self.target} %*'
        with open(wrapper_path, "w") as f:
            f.write(f"@echo off\n{cmd}")

        return self._get_short_path(wrapper_path)

    def _get_cross_env(self, sysconfig_dir=None):
        """Generates the environment variables for build."""
        if not self.zig_exe:
            print("[AndroidBuilder] Zig not available.")
            return os.environ.copy()

        zig_safe = self._get_short_path(self.zig_exe)
        env = os.environ.copy()

        # Inject Scripts path for ninja/meson
        scripts = os.path.join(os.path.dirname(sys.executable), "Scripts")
        if scripts not in env.get("PATH", ""):
            env["PATH"] = scripts + os.pathsep + env.get("PATH", "")

        # --- ZIG COMPILER SETUP ---
        target = self.target

        env["CC"] = f"{zig_safe} cc -target {target}"
        env["CXX"] = f"{zig_safe} c++ -target {target}"
        env["LD"] = f"{zig_safe} cc -target {target}"
        env["AR"] = f"{zig_safe} ar"
        env["RANLIB"] = f"{zig_safe} ranlib"

        # Helper for Rust/Cargo linking
        cargo_linker = self._create_linker_wrapper()
        if cargo_linker:
            env["CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER"] = cargo_linker
            env["RUSTFLAGS"] = "-C link-arg=-Wl,--allow-shlib-undefined"
        else:
            env["CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER"] = zig_safe
            env["RUSTFLAGS"] = (
                f"-C linker={zig_safe} -C link-arg=-target -C link-arg={target}"
            )

        # NDK/Library Paths
        if self.ndk_info:
            lib_path = self.ndk_info["lib"]
            inc = self.ndk_info["include"]
            py_inc = self.ndk_info.get("py_include")

            # Link OpenSSL if it's inside the sysroot/support package
            if py_inc:
                # The py_inc usually looks like: .../python-target/usr/include/python3.x
                # The libs are at: .../python-target/usr/lib
                py_root = os.path.dirname(os.path.dirname(os.path.dirname(py_inc)))
                env["OPENSSL_DIR"] = py_root
                env["OPENSSL_LIB_DIR"] = os.path.join(py_root, "usr", "lib")
                env["OPENSSL_INCLUDE_DIR"] = os.path.join(py_root, "usr", "include")

                # Maturin/Cargo specific overrides for cross-builds
                env["AARCH64_LINUX_ANDROID_OPENSSL_DIR"] = py_root
                env["AARCH64_LINUX_ANDROID_OPENSSL_LIB_DIR"] = env["OPENSSL_LIB_DIR"]
                env["AARCH64_LINUX_ANDROID_OPENSSL_INCLUDE_DIR"] = env[
                    "OPENSSL_INCLUDE_DIR"
                ]

            # --- OPENSSL VENDORED STRATEGY (The "Boss Fight" fix) ---
            # Using vendored=1 tells rust-openssl to download/build its own source for Android.
            # static=1 ensures it's bundled into the .so to avoid missing library errors on Android.
            env["OPENSSL_VENDORED"] = "1"
            env["OPENSSL_STATIC"] = "1"

            env["LIBRARY_PATH"] = lib_path
            usr_root = self._norm(os.path.join(self.ndk_info["sysroot"], "usr"))
            env["ZLIB_ROOT"] = usr_root
            env["JPEG_ROOT"] = usr_root

            # Combine standard Android headers with Python-specific ones
            all_inc = inc
            if py_inc:
                all_inc = f"{py_inc}{os.pathsep}{inc}"

            env["C_INCLUDE_PATH"] = all_inc
            env["CPLUS_INCLUDE_PATH"] = all_inc

            env["CFLAGS"] = f'-fPIC -O3 -DANDROID -I"{inc}"'
            if py_inc:
                env["CFLAGS"] += f' -I"{py_inc}"'

            # Android security hardening: relro/now, and prevent undefined symbols
            env["LDFLAGS"] = (
                f'-L"{lib_path}" -lz -lm -Wl,--no-undefined -Wl,-z,relro -Wl,-z,now'
            )

        # Python Config Spoofing
        env["_PYTHON_SYSCONFIGDATA_NAME"] = f"_sysconfigdata__linux_{target}"
        env["_PYTHON_HOST_PLATFORM"] = f"linux-{self.arch}"

        if sysconfig_dir:
            env["PYTHONPATH"] = (
                f"{sysconfig_dir}{os.pathsep}{env.get('PYTHONPATH', '')}"
            )

        return env

    def _generate_meson_cross(self, dest_dir):
        """Generates a Meson cross-build file to force Android/Zig toolchain."""
        cross_path = os.path.join(dest_dir, "pytron_android_cross.ini")
        zig_exe = self._get_short_path(self.zig_exe)

        # Determine CPU family
        cpu_family = "aarch64" if self.arch == "aarch64" else "x86_64"
        cpu = "armv8-a" if self.arch == "aarch64" else "x86-64"

        content = f"""
[constants]
zig_cmd = '{zig_exe}'
target = '{self.target}'

[binaries]
c = [zig_cmd, 'cc', '-target', target]
cpp = [zig_cmd, 'c++', '-target', target]
ar = [zig_cmd, 'ar']
ranlib = [zig_cmd, 'ranlib']
strip = [zig_cmd, 'strip']
pkg-config = 'false'

[properties]
cpu_family = '{cpu_family}'
cpu = '{cpu}'
endian = 'little'
os = 'linux'

[host_machine]
system = 'linux'
cpu_family = '{cpu_family}'
cpu = '{cpu}'
endian = 'little'
"""
        with open(cross_path, "w", encoding="utf-8") as f:
            f.write(content)
        return cross_path

    def build_wheel(self, package, output_dir, cpp_include=None):
        """Builds a wheel using the minimalist architecture Logic."""
        # 0. Try to fetch pre-built wheel first
        if self._fetch_prebuilt_wheel(package, output_dir):
            # If found, we still run repair/flattening just in case
            for whl in os.listdir(output_dir):
                if whl.endswith(".whl"):
                    self.repair_wheel(os.path.join(output_dir, whl))
            return True

        self._ensure_tools()
        if not self.zig_exe:
            print("[AndroidBuilder] Zig not initialized.")
            return False

        # Work in a short path if possible to avoid Windows MAX_PATH issues
        # Try C:\pytron_build if it exists, else use standard tempdir
        base_build_path = "C:\\pytron_build" if os.path.exists("C:\\") else None
        if base_build_path and not os.path.exists(base_build_path):
            try:
                os.makedirs(base_build_path, exist_ok=True)
            except Exception:
                base_build_path = None

        temp_dir = tempfile.mkdtemp(prefix="pb_", dir=base_build_path)
        source_dir = None

        try:
            if os.path.exists(package) and os.path.isdir(package):
                source_dir = package
            else:
                print(f"[AndroidBuilder] Downloading source for {package}...")
                # CRITICAL: Use --no-build-isolation here too to prevent metadata parsing crashes
                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "download",
                        package,
                        "--no-binary",
                        ":all:",
                        "--no-deps",
                        "--no-build-isolation",
                        "--dest",
                        temp_dir,
                    ]
                )  # nosec B603
                archives = [
                    f for f in os.listdir(temp_dir) if f.endswith((".tar.gz", ".zip"))
                ]
                if not archives:
                    return False
                shutil.unpack_archive(os.path.join(temp_dir, archives[0]), temp_dir)
                for item in os.listdir(temp_dir):
                    if os.path.isdir(os.path.join(temp_dir, item)):
                        source_dir = os.path.join(temp_dir, item)
                        break

            if not source_dir:
                return False

            # 1. Ensure Host Build Tools (Minimalist Requirement)
            print("[AndroidBuilder] Ensuring host build tools...")
            build_deps = [
                "wheel",
                "setuptools",
                "Cython",
                "meson-python",
                "maturin",
                "pybind11",
                "scikit-build-core",
                "ninja",
                "meson",
            ]
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install"] + build_deps,
                    env=os.environ.copy(),
                )  # nosec B603
            except Exception:
                # Silently ignore if build dependencies are already present or network fails
                pass

            # 2. Setup Spoofed Environment
            self._generate_sysconfig(source_dir)
            cross_file = self._generate_meson_cross(source_dir)
            env = self._get_cross_env(sysconfig_dir=source_dir)

            # Pass Meson cross file to any builds that use Meson (NumPy, SciPy)
            env["MESON_CROSS_FILE"] = cross_file
            # Force NumPy to use our cross file
            env["NPY_NUMPY_CROSS_FILE"] = cross_file

            if cpp_include:
                env["CFLAGS"] = env.get("CFLAGS", "") + f' -I"{cpp_include}"'

            # 3. Detect Build System
            is_maturin = False
            pyproject_path = os.path.join(source_dir, "pyproject.toml")
            if os.path.exists(pyproject_path):
                with open(pyproject_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "maturin" in content:
                        is_maturin = True

            # 4. Execute Build
            if is_maturin:
                print(f"[AndroidBuilder] Building {package} with Maturin...")
                subprocess.check_call(
                    ["rustup", "target", "add", "aarch64-linux-android"]
                )

                # Maturin cross-compilation: --interpreter expects 'python3.x' not a full path
                py_version_str = (
                    f"python{sys.version_info.major}.{sys.version_info.minor}"
                )

                cmd = [
                    sys.executable,
                    "-m",
                    "maturin",
                    "build",
                    "--release",
                    "--interpreter",
                    py_version_str,
                    "--target",
                    "aarch64-linux-android",
                    "--out",
                    output_dir,
                    "--strip",
                ]
                subprocess.check_call(cmd, cwd=source_dir, env=env)
            else:
                print(
                    f"[AndroidBuilder] Building {package} with Pip/Zig (Isolation OFF)..."
                )

                # Check for Meson projects (NumPy) or standard setuptools
                meson_cross = os.path.join(source_dir, "cross-file.meson")

                cmd = [
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    ".",
                    "--no-deps",
                    "--no-build-isolation",
                    "--wheel-dir",
                    output_dir,
                    "-v",
                ]

                # Force Meson to use our cross file if building NumPy/Scientific stack
                if os.path.exists(os.path.join(source_dir, "meson.build")):
                    env["MESON_ARGS"] = f"--cross-file {meson_cross}"

                subprocess.check_call(cmd, cwd=source_dir, env=env)

            # 5. Fix Wheel Tags (Minimalist Architecture requirement)
            self._rename_wheel(output_dir)

            # 6. Repaire and Flatten Dependencies (Independent Architecture requirement)
            for whl in os.listdir(output_dir):
                if whl.endswith(".whl"):
                    self.repair_wheel(os.path.join(output_dir, whl))

            return True

        except Exception as e:
            print(f"[AndroidBuilder] Build failed: {e}")
            return False
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
