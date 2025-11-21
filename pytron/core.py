import webview
import sys
import os

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), relative_path)


class Window:
    def __init__(self, title, url=None, html=None, js_api=None, width=800, height=600, 
                 resizable=True, fullscreen=False, min_size=(200, 100), hidden=False, 
                 frameless=False, easy_drag=True, on_loaded=None, on_closing=None, 
                 on_closed=None, on_shown=None, on_minimized=None, on_maximized=None, 
                 on_restored=None, on_resized=None, on_moved=None):
        self.title = title
        self.url = url
        self.html = html
        self.js_api = js_api
        self.width = width
        self.height = height
        self.resizable = resizable
        self.fullscreen = fullscreen
        self.min_size = min_size
        self.hidden = hidden
        self.frameless = frameless
        self.easy_drag = easy_drag
        
        # Events
        self.on_loaded = on_loaded
        self.on_closing = on_closing
        self.on_closed = on_closed
        self.on_shown = on_shown
        self.on_minimized = on_minimized
        self.on_maximized = on_maximized
        self.on_restored = on_restored
        self.on_resized = on_resized
        self.on_moved = on_moved
        
        self._window = None
        self._exposed_functions = {}

    def expose(self, func, name=None):
        """
        Expose a Python function to JavaScript.
        If name is not provided, the function name is used.
        """
        if name is None:
            name = func.__name__
        self._exposed_functions[name] = func

    def minimize(self):
        if self._window:
            self._window.minimize()

    def maximize(self):
        if self._window:
            self._window.maximize()

    def restore(self):
        if self._window:
            self._window.restore()

    def toggle_fullscreen(self):
        if self._window:
            self._window.toggle_fullscreen()
            
    def resize(self, width, height):
        if self._window:
            self._window.resize(width, height)
            
    def move(self, x, y):
        if self._window:
            self._window.move(x, y)
            
    def destroy(self):
        if self._window:
            self._window.destroy()
            
    @property
    def on_top(self):
        if self._window:
            return self._window.on_top
    
    @on_top.setter
    def on_top(self, on_top):
        if self._window:
            self._window.on_top = on_top

    def load_url(self, url):
        if self._window:
            self._window.load_url(url)
            
    def load_html(self, content, base_uri=None):
        if self._window:
            self._window.load_html(content, base_uri)

    def _build_api(self):
        # Create a dictionary of methods to expose
        methods = {}
        
        # 1. Add existing js_api methods
        if self.js_api:
            for attr_name in dir(self.js_api):
                if not attr_name.startswith('_'):
                    attr = getattr(self.js_api, attr_name)
                    if callable(attr):
                        methods[attr_name] = attr

        # 2. Add explicitly exposed functions
        for name, func in self._exposed_functions.items():
            def wrapper(self, *args, _func=func, **kwargs):
                return _func(*args, **kwargs)
            methods[name] = wrapper

        # 3. Add window management methods automatically
        # We expose them with a prefix or just as is? 
        # Let's expose them as 'window_minimize', 'window_close', etc. to avoid conflicts
        # or just expose them directly if we want a clean API.
        # Let's go with direct names but be careful.
        
        window_methods = {
            'minimize': self.minimize,
            'maximize': self.maximize,
            'restore': self.restore,
            'close': self.destroy,
            'toggle_fullscreen': self.toggle_fullscreen,
        }

        for name, func in window_methods.items():
            # Only add if not already defined by user
            if name not in methods:
                def wrapper(self, *args, _func=func, **kwargs):
                    return _func(*args, **kwargs)
                methods[name] = wrapper
            
        # Create the dynamic class
        DynamicApi = type('DynamicApi', (object,), methods)
        
        # Return an instance of this class
        api_instance = DynamicApi()
        print(f"[Pytron] Built API with methods: {list(methods.keys())}")
        return api_instance

    def create(self):
        # Build the final API object
        final_api = self._build_api()
        
        self._window = webview.create_window(
            self.title,
            url=self.url,
            html=self.html,
            js_api=final_api,
            width=self.width,
            height=self.height,
            resizable=self.resizable,
            fullscreen=self.fullscreen,
            min_size=self.min_size,
            hidden=self.hidden,
            frameless=self.frameless,
            easy_drag=self.easy_drag
        )
        
        # Bind events
        if self.on_loaded: self._window.events.loaded += self.on_loaded
        if self.on_closing: self._window.events.closing += self.on_closing
        if self.on_closed: self._window.events.closed += self.on_closed
        if self.on_shown: self._window.events.shown += self.on_shown
        if self.on_minimized: self._window.events.minimized += self.on_minimized
        if self.on_maximized: self._window.events.maximized += self.on_maximized
        if self.on_restored: self._window.events.restored += self.on_restored
        if self.on_resized: self._window.events.resized += self.on_resized
        if self.on_moved: self._window.events.moved += self.on_moved

class App:
    def __init__(self):
        self.windows = []
        self.is_running = False

    def create_window(self, title, url=None, html=None, js_api=None, width=800, height=600, **kwargs):
        window = Window(title, url, html, js_api, width, height, **kwargs)
        self.windows.append(window)
        
        # If the app is already running, create the window immediately.
        # Otherwise, wait until run() is called to allow for configuration (e.g. expose).
        if self.is_running:
            window.create()
            
        return window

    def run(self, debug=False, menu=None):
        self.is_running = True
        # Create any pending windows
        for window in self.windows:
            if window._window is None:
                window.create()
                
        # pywebview.start() is a blocking call that runs the GUI loop
        # Menu is passed to start() in pywebview
        webview.start(debug=debug, menu=menu)
        self.is_running = False

    def quit(self):
        for window in self.windows:
            window.destroy()
