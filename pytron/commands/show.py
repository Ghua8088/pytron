import argparse
import subprocess
from pathlib import Path
from .helpers import get_venv_python_path

def cmd_show(args: argparse.Namespace) -> int:
    """
    Shows list of installed packages in the virtual environment.
    """
    venv_dir = Path('env')
    venv_python = get_venv_python_path(venv_dir)
    
    if not venv_python.exists():
        print(f"[Pytron] Virtual environment not found at {venv_dir}. Run 'pytron install' first.")
        return 1

    print(f"[Pytron] Installed packages in {venv_dir}:")
    try:
        subprocess.check_call([str(venv_python), '-m', 'pip', 'list'])
    except subprocess.CalledProcessError as e:
        print(f"[Pytron] Error listing packages: {e}")
        return 1
    
    return 0
