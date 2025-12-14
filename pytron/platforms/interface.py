class PlatformInterface:
    def minimize(self, w): pass
    def set_bounds(self, w, x, y, width, height): pass
    def close(self, w): pass
    def toggle_maximize(self, w): return False
    def make_frameless(self, w): pass
    def start_drag(self, w): pass
    def message_box(self, w, title, message, style=0): return 6 # Default Yes
