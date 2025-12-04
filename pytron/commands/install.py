import argparse
import sys
import subprocess
import venv
import json
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
        # Install specific packages
        print(f"[Pytron] Installing: {', '.join(packages_to_install)}")
        try:
            subprocess.check_call([str(venv_python), '-m', 'pip', 'install'] + packages_to_install)
            
            # Add to requirements.json if not already present
            updated = False
            for pkg in packages_to_install:
                # Simple check, doesn't handle version specifiers complexity perfectly but good for now
                if pkg not in current_deps:
                    current_deps.append(pkg)
                    updated = True
            
            if updated:
                req_data["dependencies"] = current_deps
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
            # Install all at once
            subprocess.check_call([str(venv_python), '-m', 'pip', 'install'] + current_deps)
            print("[Pytron] Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"[Pytron] Error installing dependencies: {e}")
            return 1

    return 0
