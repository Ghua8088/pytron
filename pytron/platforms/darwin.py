import ctypes
import ctypes.util
from ..bindings import lib
from .interface import PlatformInterface

class DarwinImplementation(PlatformInterface):
    def __init__(self):
        try:
            # Load Cocoa
            self.cocoa = ctypes.cdll.LoadLibrary(ctypes.util.find_library('Cocoa'))
            
            # Setup objc_msgSend
            self.objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
            
            self.objc.objc_getClass.restype = ctypes.c_void_p
            self.objc.objc_getClass.argtypes = [ctypes.c_char_p]
            
            self.objc.sel_registerName.restype = ctypes.c_void_p
            self.objc.sel_registerName.argtypes = [ctypes.c_char_p]
            
            self.objc.objc_msgSend.restype = ctypes.c_void_p
            # Do NOT set argtypes for objc_msgSend as it is variadic
            # self.objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            
        except Exception as e:
            print(f"Pytron Warning: Cocoa/ObjC not found: {e}")
            self.objc = None

    def _get_window(self, w):
        return lib.webview_get_window(w) 

    def _call(self, obj, selector, *args):
        if not self.objc: return None
        sel = self.objc.sel_registerName(selector.encode('utf-8'))
        return self.objc.objc_msgSend(obj, sel, *args)
    
    # Helper for boolean args (True/False -> 1/0)
    def _bool(self, val):
        return 1 if val else 0
        
    def minimize(self, w):
        win = self._get_window(w)
        self._call(win, "miniaturize:", None)

    def set_bounds(self, w, x, y, width, height):
        win = self._get_window(w)
        # Create NSRect (x, y, w, h) - Struct handling in ctypes is needed for SetFrame
        # This is complex in pure ctypes without defining structures. 
        # Simplified approach: many simple Cocoa calls take primitives, but setFrame:display: takes a struct.
        # We might skip exact bounds setting for now or implement NSRect struct.
        pass 

    def close(self, w):
        win = self._get_window(w)
        self._call(win, "close")

    def toggle_maximize(self, w):
        win = self._get_window(w)
        self._call(win, "zoom:", None)
        return True # Approximation

    def make_frameless(self, w):
        win = self._get_window(w)
        # NSWindowStyleMaskBorderless = 0
        # NSWindowStyleMaskResizable = 8
        # setStyleMask: 8
        self._call(win, "setStyleMask:", 8)
        self._call(win, "setTitlebarAppearsTransparent:", 1)
        self._call(win, "setTitleVisibility:", 1) # NSWindowTitleHidden

    def start_drag(self, w):
        win = self._get_window(w)
        # performWindowDragWithEvent: requires an event.
        # movableByWindowBackground is cleaner
        self._call(win, "setMovableByWindowBackground:", 1)

    def message_box(self, w, title, message, style=0):
        # Use osascript for native-look dialogs
        import subprocess
        # Styles handling for osascript:
        # 0 (OK) -> display alert ... buttons {"OK"}
        # 4 (Yes/No) -> display alert ... buttons {"No", "Yes"} default button "Yes"
        
        script = ""
        if style == 4:
            script = f'display alert "{title}" message "{message}" buttons {{"No", "Yes"}} default button "Yes"'
        elif style == 1:
            script = f'display alert "{title}" message "{message}" buttons {{"Cancel", "OK"}} default button "OK"'
        else:
            script = f'display alert "{title}" message "{message}" buttons {{"OK"}} default button "OK"'
            
        try:
            output = subprocess.check_output(['osascript', '-e', script], text=True)
            # Output format: "button returned:Yes\n"
            if "Yes" in output or "OK" in output:
                return 6 if style == 4 else 1
            return 7 if style == 4 else 2
        except subprocess.CalledProcessError:
            return 7 if style == 4 else 2 # User cancel usually raises error in some contexts or returns Cancel
        except Exception:
            return 6 # Allow default if osascript fails?

    def register_pytron_scheme(self, w, root_path):
        """
        Enables file access on macOS WKWebView to bypass CORS issues.
        """
        if not self.objc: return

        try:
            # 1. Helpers for ObjC interactions
            def get_class(name):
                return self.objc.objc_getClass(name.encode('utf-8'))
            
            def str_to_nsstring(s):
                cls = get_class("NSString")
                sel = self.objc.sel_registerName("stringWithUTF8String:".encode('utf-8'))
                # Cast msgSend for (void_p, void_p, char_p) -> void_p
                f = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p)(self.objc.objc_msgSend)
                return f(cls, sel, s.encode('utf-8'))

            def bool_to_nsnumber(b):
                cls = get_class("NSNumber")
                sel = self.objc.sel_registerName("numberWithBool:".encode('utf-8'))
                # Cast msgSend for (void_p, void_p, bool) -> void_p
                f = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool)(self.objc.objc_msgSend)
                return f(cls, sel, b)

            # 2. Get the WebView
            # Window -> ContentView (usually the WKWebView in zserge/webview implementation)
            win = self._get_window(w)
            
            # Need to invoke [win contentView]
            # msgSend(win, sel)
            f_id = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(self.objc.objc_msgSend)
            sel_contentView = self.objc.sel_registerName("contentView".encode('utf-8'))
            webView = f_id(win, sel_contentView)

            if not webView:
                print("[Pytron] Could not find WebView (contentView is null).")
                return

            # 3. Get Configuration: [webView configuration]
            sel_config = self.objc.sel_registerName("configuration".encode('utf-8'))
            config = f_id(webView, sel_config)

            # 4. Get Preferences: [config preferences]
            sel_prefs = self.objc.sel_registerName("preferences".encode('utf-8'))
            prefs = f_id(config, sel_prefs)

            # 5. Set Values using KVC: [prefs setValue:val forKey:key]
            # setValue:forKey: signature: (id, SEL, id, NSString*)
            f_kv = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(self.objc.objc_msgSend)
            sel_setValue = self.objc.sel_registerName("setValue:forKey:".encode('utf-8'))

            val_true = bool_to_nsnumber(True)
            
            # Allow File Access
            key_file = str_to_nsstring("allowFileAccessFromFileURLs")
            f_kv(prefs, sel_setValue, val_true, key_file)
            print("[Pytron] macOS: Enabled allowFileAccessFromFileURLs")
            
            # Allow Universal Access (bonus) - might not exist on all versions but usually safe to set via KVC
            # key_univ = str_to_nsstring("allowUniversalAccessFromFileURLs") # Often restricted?
            # f_kv(prefs, sel_setValue, val_true, key_univ)

            # Developer Extras (Inspector)
            key_dev = str_to_nsstring("developerExtrasEnabled")
            f_kv(prefs, sel_setValue, val_true, key_dev)
            
            # Also try setting on checking for 'setValue:forKey:' on the configuration object itself?
            # Some older API might be different, but preferences object is standard for WKWebView.

        except Exception as e:
            print(f"[Pytron] Error enabling file access on macOS: {e}")
