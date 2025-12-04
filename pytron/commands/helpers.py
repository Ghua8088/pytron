from __future__ import annotations
import shutil
import subprocess
import json
import sys
from pathlib import Path

def get_venv_python_path(venv_dir: Path = Path('env')) -> Path:
    if sys.platform == 'win32':
        return venv_dir / 'Scripts' / 'python.exe'
    return venv_dir / 'bin' / 'python'

def get_python_executable() -> str:
    venv_python = get_venv_python_path()
    if venv_python.exists():
        return str(venv_python)
    return sys.executable

def get_venv_site_packages(python_exe: str) -> list[str]:
    """
    Get the site-packages directories for the given python executable.
    """
    try:
        # We use a subprocess to ask the venv python where its site-packages are.
        # We use json to safely parse the list.
        cmd = [
            python_exe, 
            '-c', 
            'import site; import json; print(json.dumps(site.getsitepackages()))'
        ]
        output = subprocess.check_output(cmd, text=True).strip()
        return json.loads(output)
    except Exception as e:
        print(f"[Pytron] Warning: Could not determine site-packages for {python_exe}: {e}")
        return []

def locate_frontend_dir(start_dir: Path | None = None) -> Path | None:
    base = (start_dir or Path('.')).resolve()
    if not base.exists():
        return None
    candidates = [base]
    candidates.extend([p for p in base.iterdir() if p.is_dir()])
    for candidate in candidates:
        pkg = candidate / 'package.json'
        if not pkg.exists():
            continue
        try:
            data = json.loads(pkg.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(data.get('scripts'), dict) and 'build' in data['scripts']:
            return candidate.resolve()
    return None


def run_frontend_build(frontend_dir: Path) -> bool | None:
    npm = shutil.which('npm')
    if not npm:
        print('[Pytron] npm not found, skipping frontend build.')
        return None
    print(f"[Pytron] Building frontend at: {frontend_dir}")
    try:
        subprocess.run(['npm', 'run', 'build'], cwd=str(frontend_dir), shell=True, check=True)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"[Pytron] Frontend build failed: {exc}")
        return False
