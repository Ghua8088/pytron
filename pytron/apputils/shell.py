import os
import sys
import subprocess
import platform

class Shell:
    """
    Native OS Shell utilities for Pytron.
    """
    @staticmethod
    def open_external(url: str):
        """
        Opens a URL or file path in the default system browser/handler.
        """
        if platform.system() == "Windows":
            os.startfile(url)
        elif platform.system() == "Darwin":
            subprocess.run(["open", url])
        else:
            subprocess.run(["xdg-open", url])

    @staticmethod
    def show_item_in_folder(path: str):
        """
        Opens the folder containing the file and selects it.
        """
        path = os.path.abspath(path)
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", path])
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", path])
        else:
            # Linux doesn't have a universal 'select' but we can open the dir
            subprocess.run(["xdg-open", os.path.dirname(path)])

    @staticmethod
    def trash_item(path: str):
        """
        Moves a file to the system trash/recycle bin.
        Requires 'send2trash' library if available, else fails.
        """
        try:
            from send2trash import send2trash
            send2trash(path)
            return True
        except ImportError:
            # Fallback or warning
            return False
