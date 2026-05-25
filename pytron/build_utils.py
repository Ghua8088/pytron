import sys
import os


def get_safe_linker_flags(module_name, build_dir):
    """
    Returns RUSTFLAGS to prevent symbol collisions on Linux and macOS
    by hiding all symbols except the Python module entry point.
    """
    flags = []

    # 1. Base hidden visibility
    # Some linkers support this directly via flags.
    # For Rust, we often rely on the version script/export list to demote others to local.

    if sys.platform.startswith("linux"):
        # Create a Linker Version Script
        os.makedirs(build_dir, exist_ok=True)
        version_script = os.path.join(build_dir, f"{module_name}.version")

        # We only export the PyInit function.
        # local: *; makes everything else hidden.
        content = f"""{{
    global:
        PyInit_{module_name};
    local:
        *;
}};
"""
        with open(version_script, "w") as f:
            f.write(content)

        flags.append(f"-Clink-arg=-Wl,--version-script={version_script}")
        # Also exclude-libs ALL helps prevent symbols from static libs leaking out
        flags.append("-Clink-arg=-Wl,--exclude-libs,ALL")

    elif sys.platform == "darwin":
        # macOS symbols in the linker often have a leading underscore, but rustc
        # already generates an exported_symbols_list for cdylib targets, so we must
        # NOT use -exported_symbol here as it will conflict.
        # We only need -undefined dynamic_lookup to allow linking against Python symbols
        # provided at runtime.
        flags.append("-Clink-arg=-Wl,-undefined,dynamic_lookup")

    return flags
