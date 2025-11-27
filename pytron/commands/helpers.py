from __future__ import annotations
import shutil
import subprocess
import json
from pathlib import Path

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
