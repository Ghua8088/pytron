from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Iterable, Optional


def generate_nuclear_hooks(
    output_dir: Path,
    collect_all_mode: bool = True,
    blacklist: Optional[Iterable[str]] = None,
    search_path: Optional[list[str]] = None,
    whitelist: Optional[Iterable[str]] = None,
) -> None:
    """
    Scans the current Python environment and writes PyInstaller hook files that
    call `collect_all` (or `collect_submodules` if `collect_all_mode` is False)
    for each installed distribution. Hooks are written as `hook-<package>.py`.

    Parameters:
    - output_dir: directory to place generated hook files
    - collect_all_mode: if True use `collect_all`, else use `collect_submodules`
    - blacklist: optional iterable of package names to skip (case-insensitive)
    - search_path: optional list of paths to search for distributions (defaults to sys.path)
    - whitelist: optional iterable of package names to ONLY include (overrides scan)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[Pytron]  Initiating Complete Hook Generation in {output_dir}...")

    if blacklist is None:
        blacklist = [
            "pyinstaller",
            "pytron-kit",
            "setuptools",
            "pip",
            "wheel",
            "altgraph",
            "pefile",
            "pyinstaller-hooks-contrib",
        ]

    bl = {n.lower() for n in blacklist}
    wl = {n.lower() for n in whitelist} if whitelist else None

    count = 0
    # Use the provided search_path if available
    dists = (
        importlib_metadata.distributions(path=search_path)
        if search_path
        else importlib_metadata.distributions()
    )

    for dist in dists:
        # Try to obtain a project/distribution name comparable to pkg_resources' project_name
        name = None
        try:
            # metadata is an email.message.Message mapping; 'Name' is the canonical key
            name = dist.metadata.get("Name") or getattr(dist, "name", None)
        except Exception:
            try:
                name = getattr(dist, "name", None)
            except Exception:
                name = None

        if not name:
            # fallback: try the package root name derived from the distribution path
            try:
                name = Path(dist.locate_file("")).name
            except Exception:
                continue

        packages = []
        try:
            top_level = dist.read_text("top_level.txt")
            if top_level:
                packages = [p.strip() for p in top_level.splitlines() if p.strip()]
        except Exception:
            pass

        # Determine if this dist should be whitelisted based on Name or provided Packages
        if wl is not None:
            should_include = name.lower() in wl
            if not should_include:
                # Check if any of its packages are in the whitelist
                for p in packages:
                    if p.lower() in wl:
                        should_include = True
                        break
            if not should_include:
                continue

        if name.lower() in bl:
            continue

        safe_name = name.replace("-", "_")

        # Robust templates: use BOTH project name and detected packages
        targets = [name] + [p for p in packages if p != name]

        body_lines = []
        for target in targets:
            body_lines.append(f"""
    hiddenimports += collect_submodules('{target}')
    datas += collect_data_files('{target}')
    binaries += collect_dynamic_libs('{target}')""")

        hook_content = f"""
# Auto-generated nuclear hook for {name}
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs, copy_metadata

try:
    hiddenimports, datas, binaries = [], [], []
    datas += copy_metadata('{name}')
    {''.join(body_lines)}
except Exception:
    # Use empty defaults on error to keep build moving
    pass
"""

        hook_file = output_dir / f"hook-{safe_name}.py"
        try:
            hook_file.write_text(hook_content, encoding="utf-8")
            count += 1
        except Exception as e:
            print(f"[Pytron] Warning: failed to write hook for {name}: {e}")

    print(
        f"[Pytron] Generated {count} complete hooks. PyInstaller can't miss anything now."
    )


if __name__ == "__main__":
    generate_nuclear_hooks(Path("temp_hooks"))
