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
        
        flags.append(f"-C link-arg=-Wl,--version-script={version_script}")
        # Also exclude-libs ALL helps prevent symbols from static libs leaking out
        flags.append("-C link-arg=-Wl,--exclude-libs,ALL")

    elif sys.platform == "darwin":
        # macOS Export List
        # Note: macOS symbols in the linker often have a leading underscore
        flags.append("-C link-arg=-undefined")
        flags.append("-C link-arg=dynamic_lookup")
        flags.append(f"-C link-arg=-Wl,-exported_symbol,_PyInit_{module_name}")
        
    return " ".join(flags)
