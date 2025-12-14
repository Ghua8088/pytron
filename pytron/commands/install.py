import argparse
import sys
import subprocess
import venv
import json
import re
from pathlib import Path
from .helpers import get_venv_python_path

REQUIREMENTS_JSON = Path('requirements.json')

def load_requirements() -> dict:
    if REQUIREMENTS_JSON.exists():
        try:
            return json.loads(REQUIREMENTS_JSON.read_text())
        except json.JSONDecodeError:
            print(f"[Pytron] Warning: {REQUIREMENTS_JSON} is invalid JSON. Using empty defaults.")
    return {"dependencies": []}

def save_requirements(data: dict):
    REQUIREMENTS_JSON.write_text(json.dumps(data, indent=4))

def get_installed_packages(venv_python) -> dict[str, str]:
    """Returns a dict of {package_name: version} for all installed packages."""
    try:
        cmd = [str(venv_python), '-m', 'pip', 'list', '--format=json']
        output = subprocess.check_output(cmd, text=True).strip()
        data = json.loads(output)
        return {item['name'].lower(): item['version'] for item in data}
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {}

def get_package_name_from_source(path: Path) -> str | None:
    """Attempts to read package name from pyproject.toml."""
    try:
        pyproject = path / 'pyproject.toml'
        if pyproject.exists():
            content = pyproject.read_text(encoding='utf-8')
            # Rudimentary TOML parsing for [project] name = "..."
            match = re.search(r'(?m)^name\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1).lower()
    except Exception:
        pass
    return None

def cmd_install(args: argparse.Namespace) -> int:
    """
    Creates a virtual environment (if not exists) and installs dependencies.
    If packages are provided, installs them and adds to requirements.json.
    If no packages provided, installs from requirements.json.
    """
    venv_dir = Path('env')
    
    # 1. Create virtual environment if it doesn't exist
    if not venv_dir.exists():
        print(f"[Pytron] Creating virtual environment in {venv_dir}...")
        venv.create(venv_dir, with_pip=True)
    else:
        # Only print if we are doing a full install or explicit install to reassure user
        pass

    venv_python = get_venv_python_path(venv_dir)
    if not venv_python.exists():
        print(f"[Pytron] Error: Python executable not found at {venv_python}")
        return 1

    packages_to_install = args.packages
    req_data = load_requirements()
    current_deps = req_data.get("dependencies", [])

    if packages_to_install:
        # Warn about versionless packages
        for pkg in packages_to_install:
            # Check if it's a local path
            if Path(pkg).exists():
                pass # Local path
            elif not any(op in pkg for op in ['==', '>=', '<=', '<', '>', '@']):
                 print(f"[Pytron] Warning: No version specified for '{pkg}'. Installing latest version.")

        print(f"[Pytron] Installing: {', '.join(packages_to_install)}")
        
        # Snapshot before
        before_state = get_installed_packages(venv_python)
        
        try:
            # Install packages
            subprocess.check_call([str(venv_python), '-m', 'pip', 'install'] + packages_to_install)
            
            # Snapshot after
            after_state = get_installed_packages(venv_python)
            
            updated = False
            
            for pkg_arg in packages_to_install:
                # Resolve package name
                resolved_name = None
                
                # Case 1: Local Path (e.g., D:\lib or ./lib)
                if Path(pkg_arg).exists():
                    # Strategy A: Try to read name from source (pyproject.toml)
                    resolved_name = get_package_name_from_source(Path(pkg_arg))
                    
                    if not resolved_name:
                         # Strategy B: Heuristic from pip list diff
                         candidates = []
                         for name, ver in after_state.items():
                            if name not in before_state:
                                candidates.append(name)
                            elif before_state.get(name) != ver:
                                candidates.append(name)
                         
                         if len(candidates) == 1:
                             resolved_name = candidates[0]
                         elif len(candidates) > 1:
                             # Fuzzy match guess
                             guess = Path(pkg_arg).name.replace('-', '_').split('.')[0].lower()
                             for cand in candidates:
                                 if guess in cand or cand in guess:
                                     resolved_name = cand
                                     break

                    # Strategy C: Check folder name against installed packages
                    if not resolved_name:
                         folder_name = Path(pkg_arg).name.lower()
                         if folder_name in after_state:
                             resolved_name = folder_name
                         else:
                             norm_folder = folder_name.replace('-', '_')
                             if norm_folder in after_state:
                                 resolved_name = norm_folder
                                 
                # Case 2: Package Name (e.g., "requests")
                else:
                    match = re.split(r'[=<>@]', pkg_arg)
                    resolved_name = match[0].strip().lower()

                # Get Version & Update Config
                if resolved_name and resolved_name in after_state:
                    resolved_version = after_state[resolved_name]
                    entry = f"{resolved_name}=={resolved_version}"
                    
                    # Remove old entry if exists (replacement logic)
                    new_deps = []
                    replaced = False
                    for dep in current_deps:
                        dep_name = re.split(r'[=<>@]', dep)[0].strip().lower()
                        if dep_name == resolved_name:
                            new_deps.append(entry)
                            replaced = True
                        else:
                            new_deps.append(dep)
                    
                    if not replaced:
                        new_deps.append(entry)
                    
                    current_deps = new_deps
                    updated = True
                else:
                    print(f"[Pytron] Warning: Could not resolve installed version for '{pkg_arg}'. Skipping requirement update.")
            
            if updated:
                req_data["dependencies"] = sorted(list(set(current_deps)))
                save_requirements(req_data)
                print(f"[Pytron] Added to {REQUIREMENTS_JSON}")
                
        except subprocess.CalledProcessError as e:
            print(f"[Pytron] Error installing packages: {e}")
            return 1
    else:
        # Install from requirements.json
        if not current_deps:
            print(f"[Pytron] No dependencies found in {REQUIREMENTS_JSON}.")
            return 0
            
        print(f"[Pytron] Installing dependencies from {REQUIREMENTS_JSON}...")
        try:
            subprocess.check_call([str(venv_python), '-m', 'pip', 'install'] + current_deps)
            print("[Pytron] Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"[Pytron] Error installing dependencies: {e}")
            return 1

    return 0
