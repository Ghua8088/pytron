import argparse
import sys
import shutil
import subprocess
import json
import os
import types
from pathlib import Path
from rich.text import Text
from ..console import log, console

# Removed rich.text import previously but needed for Text.from_ansi correctly
from .helpers import (
    locate_frontend_dir,
    run_frontend_build,
    get_python_executable,
    ensure_next_config,
    get_config,
    get_sanitized_env,
)

try:
    from watchfiles import DefaultFilter
except ImportError:

    class DefaultFilter:
        def __init__(self, **kwargs):
            pass

        def __call__(self, change, path):
            return True

    # Provide a lightweight shim so tests that patch `watchfiles.watch`
    # still work when the dependency is not installed.
    shim = types.ModuleType("watchfiles")

    def _watch_stub(*args, **kwargs):
        return iter(())

    shim.DefaultFilter = DefaultFilter
    shim.watch = _watch_stub
    sys.modules.setdefault("watchfiles", shim)


class PytronFilter:
    """
    A custom filter for watchfiles that ignores common build/temp dirs.
    Only ignores them if they are subdirectories of the project root.
    """

    def __init__(self, project_root: Path = None, frontend_dir: Path = None, **kwargs):
        self.project_root = (project_root or Path.cwd()).resolve()
        self.frontend_dir = frontend_dir.resolve() if frontend_dir else None

        # Directory names to ignore ONLY if they are within the project
        self.ignore_dirs = {
            ".git",
            "__pycache__",
            "node_modules",
            "dist",
            "build",
            ".next",
            ".output",
            "coverage",
            "env",
            "venv",
            "data",
            "db",
            "storage",
            "logs",
            "temp",
            "tmp",
        }

        # Standard file extensions/patterns to always ignore
        self.ignore_entity_patterns = {
            ".db",
            ".sqlite",
            ".sqlite3",
            ".sqlite-journal",
            ".sqlite-shm",
            ".sqlite-wal",
            ".log",
            ".tmp",
            ".swp",
            ".pyc",
            ".pyo",
            ".pyd",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
        }

    def __call__(self, change, path):
        path_obj = Path(path).resolve()

        # 1. Check relative parts for ignored directories
        try:
            rel_parts = path_obj.relative_to(self.project_root).parts
            # Ignore common heavy or build directories ONLY if they are inside project root
            if any(part in self.ignore_dirs for part in rel_parts):
                return False
        except ValueError:
            # File is outside project root, ignore it for live reload
            return False

        # 2. Ignore specific database, log, and temp file extensions
        if path_obj.suffix.lower() in self.ignore_entity_patterns:
            return False

        # 3. Ignore DB transaction files without extensions
        if any(part.endswith(("-journal", "-wal", "-shm")) for part in rel_parts):
            return False

        # 4. Frontend specific ignores (ignore src/assets so HMR handles them)
        if self.frontend_dir:
            try:
                if (
                    self.frontend_dir in path_obj.parents
                    or self.frontend_dir == path_obj
                ):
                    rel = path_obj.relative_to(self.frontend_dir)
                    if any(
                        str(rel).startswith(p)
                        for p in ["src", "public", "assets", "node_modules"]
                    ):
                        return False
            except ValueError:
                pass

        # 5. Ignore hidden files (starting with .) inside the project
        # except for the root itself
        if any(part.startswith(".") and part != "." for part in rel_parts):
            # Special case: allow files in . (the project root) even if they start with . (unlikely)
            # Standard pytron practice is to ignore things like .vscode, .idea, etc.
            return False

        return True


def run_dev_mode(script: Path, extra_args: list[str], engine: str = None) -> int:
    import threading
    import time

    stop_event = threading.Event()
    try:
        from watchfiles import watch
    except ImportError:
        log(
            "watchfiles is required for --dev mode. Install it with: pip install watchfiles",
            style="error",
        )
        return 1

    frontend_dir = locate_frontend_dir(Path("."))
    watcher_filter = PytronFilter(project_root=Path.cwd(), frontend_dir=frontend_dir)

    npm_proc = None
    dev_server_url = None

    if frontend_dir:
        config = get_config()
        provider = config.get("frontend_provider", "npm")
        provider_bin = shutil.which(provider)

        if provider_bin:
            pkg_path = frontend_dir / "package.json"
            pkg_data = json.loads(pkg_path.read_text())
            scripts = pkg_data.get("scripts", {})

            if "dev" in scripts:
                log(
                    f"Found 'dev' script. Starting development server using {provider}...",
                    style="success",
                )

                # Setup Environment
                proc_env = os.environ.copy()
                dev_port = config.get("dev_port")
                if dev_port:
                    proc_env["PORT"] = str(dev_port)
                    # Force color for nicer output
                    proc_env["FORCE_COLOR"] = "1"

                # We need to capture output to find the port, so PIPE it.
                # But we also want the user to see it.
                # We'll use a thread to read stdout and look for the URL.
                npm_proc = subprocess.Popen(
                    [provider_bin, "run", "dev"],
                    cwd=str(frontend_dir),
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=proc_env,
                    text=True,
                    bufsize=1,
                )  # nosec B603

                # Scan for URL in a background thread
                import threading
                import re

                url_found_event = threading.Event()

                def scan_output():
                    nonlocal dev_server_url
                    # Regex for Local: http://localhost:PORT
                    url_regex = re.compile(r"http://localhost:\d+")
                    # Regex to strip ANSI codes (colors)
                    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

                    while npm_proc and npm_proc.poll() is None:
                        try:
                            line = npm_proc.stdout.readline()
                            if not line:
                                break
                            # Use Text.from_ansi to handle colors correctly
                            prefix = Text(f"[{provider}] ", style="dim")
                            content = Text.from_ansi(line.strip())
                            console.print(prefix + content)

                            if not dev_server_url:
                                # Strip ANSI codes to ensure clean matching
                                clean_line = ansi_escape.sub("", line)
                                match = url_regex.search(clean_line)
                                if match:
                                    dev_server_url = match.group(0)
                                    log(
                                        f"Detected Dev Server URL: {dev_server_url}",
                                        style="success",
                                    )
                                    url_found_event.set()
                        except Exception as e:
                            log(f"Error reading {provider} output: {e}", style="error")
                            break

                t = threading.Thread(target=scan_output, daemon=True)
                t.start()

                # Wait for a bit to find the URL
                print(f"[Pytron] Waiting for {provider} dev server to start...")
                url_found_event.wait(timeout=30)

                if not dev_server_url:
                    log(
                        "Warning: Could not detect dev server URL. Python app might load old build.",
                        style="warning",
                    )

            else:
                # Fallback to old behavior (build --watch)
                # Check for watch script
                try:
                    if "next" in pkg_data.get(
                        "dependencies", {}
                    ) or "next" in pkg_data.get("devDependencies", {}):
                        ensure_next_config(frontend_dir)
                except Exception:
                    pass
                args = ["run", "build"]

                if "watch" in scripts:
                    log("Found 'watch' script, using it.", style="success")
                    args = ["run", "watch"]
                else:
                    # We'll try to append --watch to build if it's vite
                    cmd_str = scripts.get("build", "")
                    if "vite" in cmd_str and "--watch" not in cmd_str:
                        log("Adding --watch to build command.")
                        args = ["run", "build", "--", "--watch"]
                    else:
                        log(
                            "No 'watch' script found, running build once.",
                            style="warning",
                        )

                log(
                    f"Starting frontend watcher: {provider} {' '.join(args)}",
                    style="dim",
                )
                # Use shell=True for Windows compatibility
                npm_proc = subprocess.Popen(
                    [provider_bin] + args,
                    cwd=str(frontend_dir),
                    shell=False,
                )  # nosec B603
        else:
            log(f"{provider} not found, skipping frontend watch.", style="warning")

    app_proc = None

    def kill_app():
        nonlocal app_proc
        if app_proc:
            if sys.platform == "win32":
                # Force kill process tree on Windows to ensure no lingering windows
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(app_proc.pid)],
                    capture_output=True,
                )
            else:
                app_proc.terminate()
                try:
                    app_proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    app_proc.kill()
            app_proc = None

    def start_app():
        nonlocal app_proc
        kill_app()
        log("Starting app...", style="info")
        # Start as a subprocess we control
        python_exe = get_python_executable()

        env = get_sanitized_env()
        if sys.platform.startswith("linux"):
            # Secondary Shield: Ensure the child process inherits these critical isolation variables.
            env["GSETTINGS_BACKEND"] = "memory"
            env["GIO_EXTRA_MODULES"] = ""
            env["GIO_MODULE_DIR"] = "/nonexistent"
            env["NO_AT_BRIDGE"] = "1"
            env["GIO_USE_VFS"] = "local"
            env["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
            env["WINIT_UNIX_BACKEND"] = "x11"

        if dev_server_url:
            env["PYTRON_DEV_URL"] = dev_server_url

        # Engine policy:
        # - honor explicit CLI/env choice
        # - default Linux away from the experimental in-process native engine
        resolved_engine = engine or os.environ.get("PYTRON_ENGINE")
        if not resolved_engine:
            resolved_engine = "chrome" if sys.platform.startswith("linux") else "native"
        env["PYTRON_ENGINE"] = resolved_engine

        app_proc = subprocess.Popen([python_exe, str(script)] + extra_args, env=env)

    def print_dev_menu():
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        # We create a grid for the shortcuts to keep them perfectly aligned
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold green", justify="right")
        table.add_column(style="white")

        table.add_row(" [r] ", "Restart Application")
        table.add_row(" [c] ", "Clear Terminal")
        table.add_row(" [q] ", "Stop Developer Mode")

        # Build the header text with some flair
        header = Text.assemble(
            (" ◈ ", "cyan bold"),
            ("Pytron Dev Mode ", "white bold"),
            ("Active", "green dim"),
        )

        panel = Panel(
            table,
            title=header,
            title_align="left",
            border_style="cyan",
            expand=False,
            padding=(1, 3),
        )
        console.print("\n")
        console.print(panel)
        console.print("[dim]  Watching for file changes in project root...[/dim]\n")

    def keyboard_listener():
        # Setup for POSIX (Linux/macOS)
        old_settings = None
        fd = None
        try:
            if sys.platform != "win32":
                import termios
                import tty

                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                # tty.setcbreak is less destructive than setraw, it keeps signals like Ctrl+C working
                tty.setcbreak(fd)
        except Exception:
            # Fallback for environments where stdin is not a TTY (e.g. some CI/Docker)
            pass

        try:
            while not stop_event.is_set():
                char = None
                try:
                    if sys.platform == "win32":
                        import msvcrt

                        if msvcrt.kbhit():
                            char = (
                                msvcrt.getch().decode("utf-8", errors="ignore").lower()
                            )
                    else:
                        import select

                        # Use select to check if input is available without blocking
                        if (
                            fd is not None
                            and select.select([sys.stdin], [], [], 0.1)[0]
                        ):
                            char = sys.stdin.read(1).lower()
                except (IOError, EOFError):
                    break  # Stdin closed

                if char:
                    if char == "r":
                        log("Manual restart triggered...", style="info")
                        start_app()
                    elif char == "c":
                        os.system("cls" if sys.platform == "win32" else "clear")
                        print_dev_menu()
                    elif char == "q":
                        log("Stopping dev mode...", style="info")
                        stop_event.set()
                        break

                # Small sleep to prevent high CPU usage on Windows
                # On POSIX, select's 0.1s timeout already handles this
                if sys.platform == "win32" or not char:
                    time.sleep(0.05)
        finally:
            if old_settings and fd is not None:
                import termios

                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    try:
        start_app()
        print_dev_menu()

        # Start keyboard listener
        k_thread = threading.Thread(target=keyboard_listener, daemon=True)
        k_thread.start()

        log(f"Watching for changes in {Path.cwd()}...", style="success")
        for changes in watch(
            str(Path.cwd()), watch_filter=watcher_filter, stop_event=stop_event
        ):
            log(f"Detected changes: {changes}", style="dim")
            # Filter out non-code changes manually if needed, but DevWatcher handles most
            start_app()

    except KeyboardInterrupt:
        pass
    except Exception as e:
        log(f"Error in dev loop: {e}", style="error")
    finally:
        kill_app()
        if npm_proc:
            log("Stopping frontend watcher...", style="dim")
            if sys.platform == "win32":
                # Force kill the process tree to avoid "Terminate batch job (Y/N)?"
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(npm_proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                try:
                    npm_proc.terminate()
                    npm_proc.wait(timeout=2)
                except Exception:
                    npm_proc.kill()

    return 0


def cmd_run(args: argparse.Namespace) -> int:
    script_path = args.script
    if not script_path:
        # Default to app.py in current directory
        script_path = "app.py"

    path = Path(script_path)
    if not path.exists():
        log(f"Script not found: {path}", style="error")
        return 1

    if not args.dev and not getattr(args, "no_build", False):
        frontend_dir = locate_frontend_dir(path.parent)
        if frontend_dir:
            result = run_frontend_build(frontend_dir)
            if result is False:
                return 1

    if args.dev:
        engine = (
            "chrome"
            if getattr(args, "chrome", False)
            else getattr(args, "engine", None)
        )
        return run_dev_mode(path, getattr(args, "extra_args", []), engine=engine)

    python_exe = get_python_executable()
    env = get_sanitized_env()
    if sys.platform.startswith("linux"):
        # Secondary Shield: Ensure the child process inherits these critical isolation variables.
        env["GSETTINGS_BACKEND"] = "memory"
        env["GIO_EXTRA_MODULES"] = ""
        env["GIO_MODULE_DIR"] = "/nonexistent"
        env["NO_AT_BRIDGE"] = "1"
        env["GIO_USE_VFS"] = "local"
        env["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
        env["WINIT_UNIX_BACKEND"] = "x11"

    if getattr(args, "chrome", False):
        engine = "chrome"
    else:
        engine = getattr(args, "engine", None) or os.environ.get("PYTRON_ENGINE")
        if not engine:
            engine = "chrome" if sys.platform.startswith("linux") else "native"
    if engine == "servo":
        log(
            "Servo engine is disabled in this release train. Falling back to chrome.",
            style="warning",
        )
        engine = "chrome"

    env["PYTRON_ENGINE"] = engine

    cmd = [python_exe, str(path)] + getattr(args, "extra_args", [])
    log(f"Running: {' '.join(cmd)}", style="dim")
    return subprocess.call(cmd, env=env)
