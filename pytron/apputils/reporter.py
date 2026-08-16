import os
import sys
import datetime
import traceback
from .component import AppComponent


class CrashReporter(AppComponent):
    """Handles global exception hooks and crash logging."""

    def setup(self):
        """Registers the global exception hook."""
        sys.excepthook = self._handle_exception

    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """Global exception hook implementation."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        crash_msg = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        self._app.logger.critical(f"FATAL CRASH:\n{crash_msg}")

        # Save to storage
        try:
            crash_file = os.path.join(self._app.storage_path, "crash.log")
            with open(crash_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- CRASH AT {datetime.datetime.now()} ---\n")
                f.write(crash_msg)
        except Exception:
            pass

        # Show native alert if possible
        try:
            title = self._app.config.get("title", "Pytron App")
            msg = (
                "The application has encountered a fatal error and must close.\n\n"
                f"Details saved to: {self._app.storage_path}/crash.log"
            )
            self._app.message_box(
                f"{title} - Fatal Error",
                msg,
                style=0x10,  # MB_ICONERROR
            )
        except Exception:
            pass

        sys.exit(1)
