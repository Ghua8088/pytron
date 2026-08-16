import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from ..console import log


class AppAuditor:
    """
    The 'Crystal' Runtime Auditor.
    Executes the application under PEP 578 surveillance to capture the 'Live Code' universe.
    """

    def __init__(self, script_path: Path, timeout: int = 15):
        self.script_path = script_path
        self.timeout = timeout
        self.manifest_path = script_path.parent / "requirements.lock.json"

    def _generate_surveillance_runner(self) -> str:
        """
        Generates the Python code that acts as the audit harness.
        """
        # We need to robustly handle the user script execution
        escaped_script = (
            str(self.script_path.resolve()).replace("\\", "\\\\").replace('"', '\\"')
        )
        escaped_manifest = (
            str(self.manifest_path.resolve()).replace("\\", "\\\\").replace('"', '\\"')
        )

        return f"""
import sys
import json
import time
import threading
import os
import builtins
from pathlib import Path
import dis
import inspect
from unittest.mock import MagicMock

# --- DEFANGER (Prevention of Side Effects during Audit) ---
def _defang():
    try:
        import os, shutil, subprocess, socket
        # Mock filesystem destructive operations
        os.remove = MagicMock()
        os.rmdir = MagicMock()
        os.rename = MagicMock()
        shutil.rmtree = MagicMock()
        shutil.copy = MagicMock()
        shutil.move = MagicMock()

        # Mock subprocess execution to prevent running external commands
        subprocess.run = MagicMock()
        subprocess.Popen = MagicMock()
        subprocess.call = MagicMock()
        subprocess.check_call = MagicMock()
        subprocess.check_output = MagicMock()

        # Mock network/socket to prevent real network calls
        socket.socket = MagicMock()

        # Try to mock popular 3rd party libs if they exist
        try:
            import requests
            requests.get = MagicMock()
            requests.post = MagicMock()
            requests.request = MagicMock()
        except ImportError: pass

        try:
            import sqlite3
            sqlite3.connect = MagicMock()
        except ImportError: pass

        print("[Crystal] Side-effects defanged for audit.")
    except Exception:
        pass

_defang()

# --- SURVEILLANCE SYSTEM ---
live_modules = set()
live_files = set()
live_dlls = set()

def audit_hook(event, args):
    try:
        if event == "import":
            module, filename, sys_path, sys_meta_path, sys_path_hooks = args
            if module: live_modules.add(module)
            if filename: live_files.add(str(filename))
        elif event == "open" and len(args) > 0:
            path = args[0]
            if isinstance(path, (str, bytes, os.PathLike)):
                p_str = str(path)
                # Filter out obvious junk
                if not any(x in p_str.lower() for x in ["\\\\temp\\\\", "/tmp/", "pagefile.sys", ".pyc"]):
                     live_files.add(p_str)
        elif event in ["ctypes.dlopen", "os.add_dll_directory"]:
            path = args[0]
            if path: live_dlls.add(str(path))
    except Exception:
        pass

# --- RECURSIVE ANALYSIS SYSTEM ---
visited_objects = set()

def recursive_inspect(obj, depth=0):
    if depth > 10: return
    if id(obj) in visited_objects: return
    try:
        visited_objects.add(id(obj))
    except: return

    try:
        def _report(name, file=None):
             if name:
                 sys.audit("import", name, file, None, None, None)

        if inspect.ismodule(obj):
            _report(obj.__name__, getattr(obj, "__file__", None))
            return

        if hasattr(obj, "__module__") and obj.__module__:
            _report(obj.__module__)

        if inspect.isfunction(obj) or inspect.ismethod(obj):
            try:
                closures = inspect.getclosurevars(obj)
                for val in list(closures.globals.values()) + list(closures.nonlocals.values()):
                    recursive_inspect(val, depth+1)
            except: pass

            if hasattr(obj, "__code__"):
                for instr in dis.get_instructions(obj):
                    if instr.opname in ["IMPORT_NAME", "IMPORT_FROM"]:
                        _report(instr.argval)
    except Exception:
        pass

# --- AUDIT SYSTEM REGISTRATION ---
sys.addaudithook(audit_hook)

# --- DYNAMIC ANALYSIS HELPERS (InvincibleMock) ---
class InvincibleMock(MagicMock):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            return super().__getattr__(name)
        return InvincibleMock()
    def __call__(self, *args, **kwargs):
        return InvincibleMock()
    def __int__(self): return 1
    def __float__(self): return 1.0
    def __str__(self): return "mock"
    def __bool__(self): return True
    def __iter__(self): return iter([InvincibleMock()])
    def __getitem__(self, key): return InvincibleMock()
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def __await__(self):
        async def _mock_coro(): return InvincibleMock()
        return _mock_coro().__await__()

def audit_exposed_functions_dynamic(app):
    print(f"[Crystal] Running Deep Dynamic Execution Audit...")
    # Trace for dynamic __import__
    def trace_calls(frame, event, arg):
        if event == 'call' and frame.f_code.co_name == '__import__':
            try:
                name = frame.f_locals.get('name') or frame.f_args[0]
                if name: sys.audit("import", name, None, None, None, None)
            except: pass
        return trace_calls

    sys.settrace(trace_calls)
    try:
        for name, data in app._exposed_functions.items():
            func = data['func']
            try:
                sig = inspect.signature(func)
                dummy_args = [InvincibleMock() for _ in sig.parameters]
                func(*dummy_args)
            except Exception: pass
    finally:
        sys.settrace(None)

# --- MANIFEST DUMPER ---
def dump_manifest():
    try:
        import gc
        import pytron
        for obj in gc.get_objects():
            if isinstance(obj, pytron.App):
                print("[Crystal] Found App instance. Running Deep Audit...")
                # 1. Recursive Scan of Exposed
                for name, data in obj._exposed_functions.items():
                    recursive_inspect(data['func'])
                # 2. Dynamic execution
                audit_exposed_functions_dynamic(obj)
                break
    except Exception as e:
        print(f"[Crystal] Heuristic Scan Warning: {{e}}")

    existing_data = {{"modules": [], "files": [], "dlls": []}}
    if os.path.exists(f"{escaped_manifest}"):
        try:
            with open(f"{escaped_manifest}", "r") as f:
                 existing_data = json.load(f)
        except: pass

    data = {{
        "modules": sorted(list(set(existing_data.get("modules", []) + list(live_modules)))),
        "files": sorted(list(set(existing_data.get("files", []) + list(live_files)))),
        "dlls": sorted(list(set(existing_data.get("dlls", []) + list(live_dlls))))
    }}
    try:
        with open(f"{escaped_manifest}", "w") as f:
            json.dump(data, f, indent=4)
        print(f"[Crystal] Lock File Updated: {{len(data['modules'])}} modules, {{len(data['dlls'])}} DLLs.")
    except Exception as e:
        print(f"[Crystal] Failed to dump manifest: {{e}}")

import atexit
atexit.register(dump_manifest)

# --- MONKEY PATCHING PYTRON ---
def patch_pytron_app():
    try:
        import pytron
        OriginalApp = pytron.App
        class AuditedApp(OriginalApp):
            def expose(self, func=None, name=None, secure=False, run_in_thread=True):
                if func is not None:
                    try:
                        recursive_inspect(func)
                    except: pass
                return super().expose(func, name=name, secure=secure, run_in_thread=run_in_thread)
        pytron.App = AuditedApp
        print("[Crystal] 'pytron.App.expose' patched.")
    except Exception: pass

patch_pytron_app()

print("[Crystal] Surveillance Active. Launching Target...")
target_script = "{escaped_script}"
target_dir = os.path.dirname(target_script)
os.chdir(target_dir)
sys.path.insert(0, target_dir)

try:
    with open(target_script, "r", encoding="utf-8") as f:
        code = compile(f.read(), target_script, "exec")
        exec(code, {{'__name__': '__main__', '__file__': target_script}})
except SystemExit: pass
except Exception as e:
    print(f"[Crystal] Target Interrupted: {{e}}")

dump_manifest()
"""

    def run_audit(self) -> Optional[Dict]:
        """
        Spawns the surveillance subprocess and monitors it.
        Returns the loaded manifest data.
        """
        log("Initializing Crystal 2.0 (Deep Audit Engine)...", style="cyan")
        runner_code = self._generate_surveillance_runner()
        runner_path = self.script_path.parent / "crystal_runner.py"
        runner_path.write_text(runner_code, encoding="utf-8")

        python_exe = sys.executable

        p = None
        try:
            log(
                f"  + Launching {self.script_path.name} in audit mode (Timeout: {self.timeout}s)...",
                style="dim",
            )

            p = subprocess.Popen(
                [python_exe, str(runner_path)],
                cwd=str(self.script_path.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                stdout, stderr = p.communicate(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                log(
                    "  + Timeout reached. Harvesting captured data...",
                    style="dim",
                )
                p.terminate()
                try:
                    p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    p.kill()

            if self.manifest_path.exists():
                try:
                    data = json.loads(self.manifest_path.read_text())
                    log(
                        f"Crystal Audit Complete. Captured {len(data.get('modules', []))} live modules and {len(data.get('dlls', []))} DLLs.",
                        style="success",
                    )
                    return data
                except Exception as e:
                    log(f"Failed to parse Crystal manifest: {e}", style="error")
            else:
                log("Crystal Audit failed to produce a manifest.", style="error")

        except Exception as e:
            log(f"Crystal Surveillance Error: {e}", style="error")
        finally:
            if runner_path.exists():
                os.remove(runner_path)

        return None
