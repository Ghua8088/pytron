import argparse
import subprocess
import sys
import os
from pathlib import Path

TEMPLATE_APP = '''from pytron import App

def main():
    app = App()
    window = app.create_window()
    app.run()

if __name__ == '__main__':
    main()
'''

TEMPLATE_SETTINGS = '''{
    "title": "My Pytron App",
    "width": 800,
    "height": 600,
    "resizable": true,
    "frameless": false,
    "easy_drag": true,
    "url": "frontend/dist/index.html"
}
'''

def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    if target.exists():
        print(f"Target '{target}' already exists")
        return 1

    print(f"Creating new Pytron app at: {target}")
    target.mkdir(parents=True)

    # Create app.py
    app_file = target / 'app.py'
    app_file.write_text(TEMPLATE_APP)

    # Create settings.json
    settings_file = target / 'settings.json'
    settings_file.write_text(TEMPLATE_SETTINGS)

    # Initialize Vite React app in frontend folder
    print("Initializing Vite React app...")
    # Using npx to create vite app non-interactively
    # We need to be inside the target directory or specify path
    # npx create-vite frontend --template react
    # On Windows, npx needs shell=True
    try:
        subprocess.run(['npx', '-y', 'create-vite', 'frontend', '--template', 'react'], cwd=str(target), shell=True, check=True)
        
        # Install dependencies including pytron-client
        print("Installing dependencies...")
        subprocess.run(['npm', 'install'], cwd=str(target / 'frontend'), shell=True, check=True)
        # We should probably add pytron-client here if it was published, but for now user has to add it manually or we link it?
        # Let's just leave it as standard vite app for now as per request "vite frontend by default"
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to initialize Vite app: {e}")
        # Fallback to creating directory if failed
        frontend = target / 'frontend'
        if not frontend.exists():
            frontend.mkdir()
            (frontend / 'index.html').write_text('<!doctype html><html><body><h1>Pytron App (Vite Init Failed)</h1></body></html>')

    # Create README
    (target / 'README.md').write_text('# My Pytron App\n\nBuilt with Pytron CLI init template.\n\n## Structure\n- `app.py`: Main Python entrypoint\n- `settings.json`: Application configuration\n- `frontend/`: Vite React Frontend')

    # Create virtual environment
    print("Creating virtual environment...")
    env_dir = target / 'env'
    try:
        subprocess.run([sys.executable, '-m', 'venv', str(env_dir)], check=True)
        
        # Determine pip path in new env
        if sys.platform == 'win32':
            pip_exe = env_dir / 'Scripts' / 'pip'
            python_exe = env_dir / 'Scripts' / 'python'
            activate_script = env_dir / 'Scripts' / 'activate'
        else:
            pip_exe = env_dir / 'bin' / 'pip'
            python_exe = env_dir / 'bin' / 'python'
            activate_script = env_dir / 'bin' / 'activate'
            
        print("Installing dependencies in virtual environment...")
        # Install pytron in the new env. 
        subprocess.run([str(pip_exe), 'install', 'pytron'], check=True)
        
        # Create requirements.txt
        (target / 'requirements.txt').write_text('pytron\n')
        
        # Create helper run scripts
        if sys.platform == 'win32':
            run_script = target / 'run.bat'
            run_script.write_text('@echo off\ncall env\\Scripts\\activate.bat\npython app.py\npause')
        else:
            run_script = target / 'run.sh'
            run_script.write_text('#!/bin/bash\nsource env/bin/activate\npython app.py')
            # Make it executable
            try:
                run_script.chmod(run_script.stat().st_mode | 0o111)
            except Exception:
                pass

    except Exception as e:
        print(f"Warning: Failed to set up virtual environment: {e}")

    print('Scaffolded app files:')
    print(f' - {app_file}')
    print(f' - {settings_file}')
    print(f' - {target}/frontend')
    print(f' - {target}/env (Virtual Environment)')
    
    if sys.platform == 'win32':
        print('Run `run.bat` to start the app (automatically uses the virtual env).')
    else:
        print('Run `./run.sh` to start the app (automatically uses the virtual env).')
        
    print('Or activate manually:')
    if sys.platform == 'win32':
        print(f'  {target}\\env\\Scripts\\activate')
    else:
        print(f'  source {target}/env/bin/activate')
        
    print('Then run: pytron run')
    return 0
