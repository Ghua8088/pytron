import webview

class SystemAPI:
    """
    Built-in system capabilities exposed to every Pytron window.
    """
    def __init__(self, window_instance):
        self.window = window_instance

    def system_notification(self, title, message):
        # Pywebview doesn't have a direct notification API, so we might need a library
        # or just print for now / use OS specific command.
        # For now, let's just print to console to show it works, 
        # or use a simple ctypes message box on Windows if possible.
        print(f"[System Notification] {title}: {message}")
        # TODO: Implement native notifications
        
    def system_open_file(self, file_types=()):
        """
        Open a file dialog.
        """
        if self.window._window:
            return self.window._window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
            
    def system_save_file(self, save_filename='', file_types=()):
        """
        Open a save file dialog.
        """
        if self.window._window:
            return self.window._window.create_file_dialog(webview.SAVE_DIALOG, save_filename=save_filename, file_types=file_types)

    def system_message_box(self, title, message):
        """
        Open a message box (confirmation dialog).
        """
        if self.window._window:
            return self.window._window.create_confirmation_dialog(title, message)
