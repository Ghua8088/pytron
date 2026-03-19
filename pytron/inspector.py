import logging
import traceback
import base64
import time
import os
import sys
from collections import deque
from .serializer import pytron_serialize


class DequeHandler(logging.Handler):
    def __init__(self, maxlen=300):
        super().__init__()
        self.logs = deque(maxlen=maxlen)
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
            )
        )

    def emit(self, record):
        try:
            msg = self.format(record)
            self.logs.append(
                {
                    "time": time.strftime("%H:%M:%S"),
                    "level": record.levelname,
                    "msg": record.getMessage(),
                    "full": msg,
                }
            )
        except Exception:
            self.handleError(record)


class Inspector:
    def __init__(self, app):
        self.app = app
        self.start_time = time.time()
        self.handler = DequeHandler(maxlen=300)
        self.handler.setLevel(logging.DEBUG)

        # Add to the root logger to capture everything
        logging.getLogger().addHandler(self.handler)

        self.ipc_history = deque(maxlen=200)
        self.inspector_window = None

        # Prime psutil for CPU tracking
        self._proc = None
        try:
            import psutil

            self._proc = psutil.Process(os.getpid())
            self._proc.cpu_percent()
        except Exception as e:
            logging.debug(f"Failed to init psutil: {e}")

    def log_ipc(self, name, args, result=None, error=None, duration=0):
        """Called by the bridge when an IPC call occurs."""
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "function": name,
            "args": args,
            "result": pytron_serialize(result) if result is not None else None,
            "error": str(error) if error else None,
            "duration": round(duration * 1000, 2),  # ms
        }
        self.ipc_history.append(entry)

    def get_stats(self):
        """Returns live system and process metrics."""
        try:
            import psutil

            if not self._proc:
                self._proc = psutil.Process(os.getpid())

            # Non-blocking CPU call
            cpu = self._proc.cpu_percent()
            mem = self._proc.memory_info().rss / (1024 * 1024)
            sys_mem = psutil.virtual_memory().percent

            return {
                "process_cpu": cpu,
                "process_mem": round(mem, 2),
                "system_mem": sys_mem,
                "uptime": round(time.time() - self.start_time, 1),
                "pid": os.getpid(),
                "threads": self._proc.num_threads(),
                "platform": sys.platform,
            }
        except Exception:
            return {
                "uptime": round(time.time() - self.start_time, 1),
                "pid": os.getpid(),
            }

    def get_app_data(self):
        """Aggregated data for the dashboard."""
        try:
            win_data = []
            for i, w in enumerate(self.app.windows):
                is_vis = True
                try:
                    if hasattr(w, "is_visible") and callable(w.is_visible):
                        is_vis = w.is_visible()
                except Exception as e:
                    logging.debug(f"Failed to check visibility for window {i}: {e}")

                # Use config for more accurate metadata
                config = getattr(w, "config", {})
                win_data.append(
                    {
                        "id": i,
                        "title": config.get("title", f"Window {i}"),
                        "url": config.get("url", "N/A"),
                        "visible": is_vis,
                        "dimensions": config.get("dimensions", [0, 0]),
                    }
                )

            return {
                "state": self.app.state.to_dict(),
                "stats": self.get_stats(),
                "windows": win_data,
                "plugins": getattr(self.app, "plugin_statuses", []),
                "ipc_history": list(self.ipc_history),
            }
        except Exception as e:
            return {"error": str(e), "traceback": traceback.format_exc()}

    def get_logs(self):
        """Returns the captured logs."""
        return list(self.handler.logs)

    def log_console(self, cmd, result=None, error=None):
        """Injects a console interaction into the log stream."""
        if cmd:
            self.handler.emit(
                logging.LogRecord(
                    name="pytron.console",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f">>> {cmd}",
                    args=None,
                    exc_info=None,
                )
            )
        if result is not None:
            self.handler.emit(
                logging.LogRecord(
                    name="pytron.console",
                    level=logging.DEBUG,
                    pathname="",
                    lineno=0,
                    msg=f"<- {result}",
                    args=None,
                    exc_info=None,
                )
            )
        if error:
            self.handler.emit(
                logging.LogRecord(
                    name="pytron.console",
                    level=logging.ERROR,
                    pathname="",
                    lineno=0,
                    msg=f"Error: {error}",
                    args=None,
                    exc_info=None,
                )
            )

    def eval_code(self, code):
        """Executes arbitrary Python code in the context of the app."""
        try:
            # Check for special 'console' object or similar?
            # For now, just app/state
            try:
                res = eval(  # nosemgrep
                    code, {"app": self.app, "state": self.app.state, "inspector": self}
                )  # nosec B307
                ser_res = pytron_serialize(res)
                self.log_console(code, result=ser_res)
                return {"result": ser_res}
            except SyntaxError:
                exec_globals = {
                    "app": self.app,
                    "state": self.app.state,
                    "inspector": self,
                }
                exec(code, exec_globals)  # nosec B102 # nosemgrep
                self.log_console(code, result="Statement executed.")
                return {"result": "Statement executed successfully."}
        except Exception as e:
            err = traceback.format_exc()
            self.log_console(code, error=str(e))
            return {"error": str(e), "traceback": err}

    def _launch_inspector(self):
        """Internal: Runs the inspector window in specific thread."""
        from .inspector_ui import INSPECTOR_HTML
        import threading

        try:
            # Creation must happen on the thread that runs the loop (Windows/Tao requirement)
            logging.info("Inspector Thread: Creating Window...")

            # Create window first without a URL to avoid duplication race
            # Force framed window and 16:9 ratio (1244x700)
            window = self.app.create_window(
                title="Pytron Inspector",
                width=1244,
                height=700,
                resizable=True,
                frameless=False,
                _is_utility=True,  # Pass it here
            )
            # Mark as utility so App.run doesn't block on it
            window._is_utility = True
            window.set_prevent_close(True)  # Force hide instead of exit
            self.inspector_window = window

            # Bindings MUST be added BEFORE navigation so the protocol handler can inject them
            window.bind("inspector_get_data", self.get_app_data)
            window.bind("inspector_get_logs", self.get_logs)
            window.bind("inspector_eval", self.eval_code)
            window.bind("inspector_window_action", self.window_action)

            # Serve the HTML via the pytron:// protocol
            # Webview.serve_data now automatically handles the /app/ prefixing for routing
            inspector_url = window.serve_data(
                "inspector.html", INSPECTOR_HTML.encode("utf-8"), "text/html"
            )

            # Navigate to the served URL
            window.navigate(inspector_url)

            # Navigation happens via init now
            self._opening = False

            # Block until closed
            window.start()

        except Exception as e:
            logging.error(f"Failed to launch inspector: {e}")
        finally:
            self.inspector_window = None
            self._opening = False

    def _must_launch_on_main_thread(self):
        return (
            sys.platform.startswith("linux")
            and getattr(self.app, "engine", "native") == "native"
        )

    def toggle(self):
        # 1. Opening Guard: Prevent spamming while thread is spinning up
        if hasattr(self, "_opening") and self._opening:
            logging.info("Inspector: Already opening...")
            return

        # 2. Existing Window Guard
        if self.inspector_window:
            try:
                if self.inspector_window.is_alive():
                    logging.info(
                        "Inspector: Window exists and is alive, attempting to show..."
                    )
                    self.inspector_window.show()
                    # Attempt to un-minimize if needed
                    if hasattr(self.inspector_window, "restore"):
                        self.inspector_window.restore()
                    return
                else:
                    logging.info("Inspector: Window exists but is dead, resetting.")
                    self.inspector_window = None
            except Exception as e:
                logging.error(
                    f"Inspector: Error checking existing window (resetting): {e}"
                )
                self.inspector_window = None

        # 3. Launch
        logging.info("Inspector: Launching new thread...")
        self._opening = True
        import threading

        if self._must_launch_on_main_thread():
            if threading.current_thread() is threading.main_thread():
                logging.info("Inspector: Launching on main thread for Linux native.")
                self._launch_inspector()
            else:
                logging.warning(
                    "Inspector: Linux native inspector must be opened from the main thread. "
                    "Use app_toggle_inspector()/inspector_toggle from the app UI for now."
                )
                self._opening = False
            return

        t = threading.Thread(target=self._launch_inspector, daemon=True)
        t.start()

    def window_action(self, index, action):
        try:
            # Allow controlling other windows from inspector
            if index < len(self.app.windows):
                win = self.app.windows[index]
                if action == "show":
                    win.show()
                elif action == "hide":
                    win.hide()
                elif action == "close":
                    win.close()
                elif action == "center":
                    win.center()
            return True
        except Exception as e:
            return {"error": str(e)}
