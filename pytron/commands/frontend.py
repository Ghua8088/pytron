import argparse
import sys
import shutil
import subprocess
from pathlib import Path
from .helpers import locate_frontend_dir

def cmd_frontend_install(args: argparse.Namespace) -> int:
    """
    Installs libraries into the frontend project.
    """
    # Try to find frontend dir
    # Use current directory as robust start
    frontend_dir = locate_frontend_dir(Path('.'))
    
    if not frontend_dir:
        print("[Pytron] Error: Could not locate a frontend directory (package.json).")
        return 1
        
    print(f"[Pytron] Found frontend in: {frontend_dir}")
    
    # Check for package manager
    npm = shutil.which('npm')
    if not npm:
        print("[Pytron] Error: npm is not installed or not in PATH.")
        return 1

    packages = args.packages
    if not packages:
        # Just run install
        print("[Pytron] Running 'npm install'...")
        cmd = ['npm', 'install']
    else:
        print(f"[Pytron] Installing frontend packages: {', '.join(packages)}")
        cmd = ['npm', 'install'] + packages

    try:
        # Use shell=True on Windows for npm
        subprocess.check_call(cmd, cwd=str(frontend_dir), shell=(sys.platform == 'win32'))
        print("[Pytron] Frontend dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[Pytron] Error installing frontend packages: {e}")
        return 1

    return 0
