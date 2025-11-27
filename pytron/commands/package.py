import argparse
import sys
import shutil
import subprocess
import json
import os
from pathlib import Path

def find_makensis() -> str | None:
    path = shutil.which('makensis')
    if path:
        return path
    common_paths = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None

def build_installer(out_name: str, script_dir: Path, app_icon: str | None) -> int:
    print("[Pytron] Building installer...")
    makensis = find_makensis()
    if not makensis:
        print("[Pytron] NSIS (makensis) not found.")
        # Try to find bundled installer
        try:
            import pytron
            if pytron.__file__:
                pkg_root = Path(pytron.__file__).resolve().parent
                nsis_setup = pkg_root / 'nsis-setup.exe'
                
                if nsis_setup.exists():
                    print(f"[Pytron] Found bundled NSIS installer at {nsis_setup}")
                    print("[Pytron] Launching NSIS installer... Please complete the installation.")
                    try:
                        # Run the installer and wait
                        subprocess.run([str(nsis_setup)], check=True)
                        print("[Pytron] NSIS installer finished. Checking for makensis again...")
                        makensis = find_makensis()
                    except Exception as e:
                        print(f"[Pytron] Error running NSIS installer: {e}")
        except Exception as e:
            print(f"[Pytron] Error checking for bundled installer: {e}")

    if not makensis:
        print("Error: makensis not found. Please install NSIS and add it to PATH.")
        return 1
        
    # Locate the generated build directory and exe
    dist_dir = Path('dist')
    # In onedir mode, output is dist/AppName
    build_dir = dist_dir / out_name
    exe_file = build_dir / f"{out_name}.exe"
    
    if not build_dir.exists() or not exe_file.exists():
            print(f"Error: Could not find generated build directory or executable in {dist_dir}")
            return 1
    
    # Locate the NSIS script
    nsi_script = Path('installer.nsi')
    if not nsi_script.exists():
            if Path('installer/Installation.nsi').exists():
                nsi_script = Path('installer/Installation.nsi')
            else:
                # Check inside the pytron package
                try:
                    import pytron
                    if pytron.__file__ is not None:
                        pkg_root = Path(pytron.__file__).resolve().parent
                        pkg_nsi = pkg_root / 'installer' / 'Installation.nsi'
                        if pkg_nsi.exists():
                            nsi_script = pkg_nsi
                except ImportError:
                    pass
                
                if not nsi_script.exists():
                    print("Error: installer.nsi not found. Please create one or place it in the current directory.")
                    return 1

    build_dir_abs = build_dir.resolve()
    
    # Get version from settings if available, else default
    version = "1.0"
    try:
        settings_path = script_dir / 'settings.json'
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())
            version = settings.get('version', "1.0")
    except Exception:
        pass

    cmd_nsis = [
        makensis,
        f"/DNAME={out_name}",
        f"/DVERSION={version}",
        f"/DBUILD_DIR={build_dir_abs}",
        f"/DMAIN_EXE_NAME={out_name}.exe",
        f"/DOUT_DIR={script_dir.resolve()}",
    ]
    
    # Pass icon to NSIS if available
    if app_icon:
        abs_icon = Path(app_icon).resolve()
        cmd_nsis.append(f'/DMUI_ICON={abs_icon}')
        cmd_nsis.append(f'/DMUI_UNICON={abs_icon}')
        
    cmd_nsis.append(str(nsi_script))
    
    print(f"Running NSIS: {' '.join(cmd_nsis)}")
    return subprocess.call(cmd_nsis)


def cmd_package(args: argparse.Namespace) -> int:
    script_path = args.script
    if not script_path:
        script_path = 'app.py'

    script = Path(script_path)
    if not script.exists():
        print(f"Script not found: {script}")
        return 1

    # If the user provided a .spec file, use it directly
    if script.suffix == '.spec':
        print(f"[Pytron] Packaging using spec file: {script}")
        # When using a spec file, most other arguments are ignored by PyInstaller
        # as the spec file contains the configuration.
        cmd = [sys.executable, '-m', 'PyInstaller', str(script)]
        
        # We can still pass --noconfirm to overwrite dist/build without asking
        cmd.append('--noconfirm')
        
        print(f"Running: {' '.join(cmd)}")
        ret_code = subprocess.call(cmd)
        
        # If installer was requested, we still try to build it
        if ret_code == 0 and args.installer:
            # We need to deduce the name from the spec file or args
            # This is tricky if we don't parse the spec. 
            # Let's try to use args.name if provided, else script stem
            out_name = args.name or script.stem
            return build_installer(out_name, script.parent, args.icon)
            
        return ret_code

    out_name = args.name
    if not out_name:
        # Try to get name from settings.json
        try:
            settings_path = script.parent / 'settings.json'
            if settings_path.exists():
                settings = json.loads(settings_path.read_text())
                title = settings.get('title')
                if title:
                    # Sanitize title to be a valid filename
                    # Replace non-alphanumeric (except - and _) with _
                    out_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in title)
                    # Remove duplicate underscores and strip
                    while '__' in out_name:
                        out_name = out_name.replace('__', '_')
                    out_name = out_name.strip('_')
        except Exception:
            pass

    if not out_name:
        out_name = script.stem

    # Ensure pytron is found by PyInstaller
    import pytron
    # Dynamically find where pytron is installed on the user's system
    if pytron.__file__ is None:
        print("Error: Cannot determine pytron installation location.")
        print("This may happen if pytron is installed as a namespace package.")
        print("Try reinstalling pytron: pip install --force-reinstall pytron")
        return 1
    package_dir = Path(pytron.__file__).resolve().parent.parent
    
    # Icon handling
    # Icon handling
    app_icon = args.icon
    
    # Check settings.json for icon
    if not app_icon:
        # We already loaded settings earlier to get the title
        # But we need to make sure 'settings' variable is available here
        # It was loaded in a try-except block above, let's re-ensure we have it or reuse it
        # The previous block defined 'settings' inside try, so it might not be bound if exception occurred.
        # Let's re-load safely or assume it's empty if not found.
        pass # We will use the 'settings' dict if it exists from the block above
        
    # Re-load settings safely just in case scope is an issue or to be clean
    settings = {}
    try:
        settings_path = script.parent / 'settings.json'
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())
    except Exception:
        pass

    if not app_icon:
        config_icon = settings.get('icon')
        if config_icon:
            possible_icon = script.parent / config_icon
            if possible_icon.exists():
                # Check extension
                if possible_icon.suffix.lower() == '.png':
                    # Try to convert to .ico
                    try:
                        from PIL import Image
                        print(f"[Pytron] Converting {possible_icon.name} to .ico for packaging...")
                        img = Image.open(possible_icon)
                        ico_path = possible_icon.with_suffix('.ico')
                        img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
                        app_icon = str(ico_path)
                    except ImportError:
                        print(f"[Pytron] Warning: Icon is .png but Pillow is not installed. Cannot convert to .ico.")
                        print(f"[Pytron] Install Pillow (pip install Pillow) or provide an .ico file.")
                    except Exception as e:
                        print(f"[Pytron] Warning: Failed to convert .png to .ico: {e}")
                elif possible_icon.suffix.lower() == '.ico':
                    app_icon = str(possible_icon)
                else:
                    print(f"[Pytron] Warning: Icon file must be .ico (or .png with Pillow installed). Ignoring {possible_icon.name}")

    # Fallback to Pytron icon
    pytron_icon = package_dir / 'installer' / 'pytron.ico'
    if not app_icon and pytron_icon.exists():
        app_icon = str(pytron_icon)

    cmd = [
        sys.executable, '-m', 'PyInstaller', 
        '--onedir', 
        '--hidden-import=pytron',
        '--paths', str(package_dir),
        '--name', out_name, 
        str(script)
    ]
    
    if app_icon:
        cmd.extend(['--icon', app_icon])
        print(f"[Pytron] Using icon: {app_icon}")

    cmd.append('--noconsole')

    # Auto-detect and include assets
    add_data = []
    if args.add_data:
        add_data.extend(args.add_data)

    script_dir = script.parent
    
    # 1. settings.json
    settings_path = script_dir / 'settings.json'
    if settings_path.exists():
        # Format: source;dest (Windows) or source:dest (Unix)
        # We want settings.json to be at the root of the bundle
        add_data.append(f"{settings_path}{os.pathsep}.")
        print(f"[Pytron] Auto-including settings.json")

    # 2. Frontend assets
    # Check for frontend/dist or frontend/build
    frontend_dist = None
    possible_dists = [
        script_dir / 'frontend' / 'dist',
        script_dir / 'frontend' / 'build'
    ]
    for d in possible_dists:
        if d.exists() and d.is_dir():
            frontend_dist = d
            break
            
    if frontend_dist:
        # We want the *contents* of dist to be in a folder named 'frontend/dist' or similar?
        # Usually settings.json points to "frontend/dist/index.html"
        # So we should preserve the structure "frontend/dist" inside the bundle.
        # PyInstaller add-data "src;dest" puts src INSIDE dest.
        # So "frontend/dist;frontend/dist"
        
        # Let's verify the relative path from script
        rel_path = frontend_dist.relative_to(script_dir)
        add_data.append(f"{frontend_dist}{os.pathsep}{rel_path}")
        print(f"[Pytron] Auto-including frontend assets from {rel_path}")

    for item in add_data:
        cmd.extend(['--add-data', item])

    print(f"Packaging with: {' '.join(cmd)}")
    ret_code = subprocess.call(cmd)
    if ret_code != 0:
        return ret_code

    if args.installer:
        return build_installer(out_name, script.parent, app_icon)

    return 0
