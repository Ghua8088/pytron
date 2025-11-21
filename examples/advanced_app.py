import sys
import os
import webview

# Add the project directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pytron import App, get_resource_path
from webview.menu import Menu, MenuAction, MenuSeparator

class AdvancedApi:
    def __init__(self):
        self.count = 0
        self._window = None

    def set_window(self, window):
        self._window = window

    def increment_counter(self):
        self.count += 1
        print(f"Counter incremented to: {self.count}")
        return self.count

    def minimize_window(self):
        if self._window:
            self._window.minimize()

    def open_file(self):
        if self._window:
            # Use the pytron Window wrapper method if available, or directly on pywebview window
            # Since we passed the raw pywebview window in set_window, we use it directly.
            # Wait, in main() we passed window._window. 
            # Let's update main() to pass the wrapper instead, or just use the raw window API here.
            # The raw window object has create_file_dialog too.
            result = self._window.create_file_dialog(webview.OPEN_DIALOG)
            print(f"File selected: {result}")
            return result

    def confirm_action(self):
        if self._window:
            result = self._window.create_confirmation_dialog('Confirm', 'Are you sure you want to proceed?')
            print(f"Confirmation result: {result}")
            return result

def on_window_loaded():
    print("Window loaded successfully!")

def main():
    app = App()
    api = AdvancedApi()
    
    # Get absolute path to the HTML file
    # In frozen mode, assets are at root/assets. In dev mode, they are relative to this script.
    html_path = get_resource_path(os.path.join('assets', 'index.html'))
    
    if not os.path.exists(html_path):
        # Fallback: if get_resource_path didn't find it (e.g. dev mode weirdness), try relative to __file__
        current_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(current_dir, 'assets', 'index.html')
    
    # Create window with advanced options
    window = app.create_window(
        "Advanced Pytron App",
        url=html_path,
        js_api=api,
        width=900,
        height=700,
        frameless=True,  # We implemented a custom title bar in HTML
        easy_drag=True,  # Allow dragging by the window body (or specific regions)
        on_loaded=on_window_loaded
    )
    
    # Pass the window object to the API so it can control the window
    api.set_window(window._window) # Accessing the underlying pywebview window object

    # Define Menu
    menu_items = [
        Menu('File', [
            MenuAction('Open', api.open_file),
            MenuSeparator(),
            MenuAction('Exit', app.quit)
        ]),
        Menu('Window', [
            MenuAction('Minimize', api.minimize_window),
            MenuAction('Toggle Fullscreen', lambda: window.toggle_fullscreen())
        ]),
        Menu('Help', [
            MenuAction('About', lambda: window.create_confirmation_dialog('About', 'Pytron Advanced App v1.0'))
        ])
    ]

    # Localization example
    localization = {
        'global.quitConfirmation': 'Are you sure you want to quit?',
    }

    app.run(debug=True, menu=menu_items, localization=localization)

if __name__ == "__main__":
    main()
