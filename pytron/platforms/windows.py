import ctypes
from ..bindings import lib
from .interface import PlatformInterface

class WindowsImplementation(PlatformInterface):
    # MAGICAL CONSTANTS
    GWL_STYLE = -16
    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000
    WS_SYSMENU = 0x00080000
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000
    WM_NCLBUTTONDOWN = 0xA1
    HTCAPTION = 2
    SW_MINIMIZE = 6
    SW_MAXIMIZE = 3
    SW_RESTORE = 9
    WM_CLOSE = 0x0010
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010

    def _get_hwnd(self, w):
        return lib.webview_get_window(w)

    def minimize(self, w):
        hwnd = self._get_hwnd(w)
        ctypes.windll.user32.ShowWindow(hwnd, self.SW_MINIMIZE)

    def set_bounds(self, w, x, y, width, height):
        hwnd = self._get_hwnd(w)
        ctypes.windll.user32.SetWindowPos(hwnd, 0, int(x), int(y), int(width), int(height), self.SWP_NOZORDER | self.SWP_NOACTIVATE)

    def close(self, w):
        hwnd = self._get_hwnd(w)
        ctypes.windll.user32.PostMessageW(hwnd, self.WM_CLOSE, 0, 0)

    def toggle_maximize(self, w):
        hwnd = self._get_hwnd(w)
        # Check if zoomed
        is_zoomed = ctypes.windll.user32.IsZoomed(hwnd)
        if is_zoomed:
            ctypes.windll.user32.ShowWindow(hwnd, self.SW_RESTORE)
            return False 
        else:
            ctypes.windll.user32.ShowWindow(hwnd, self.SW_MAXIMIZE)
            return True

    def make_frameless(self, w):
        """
        Surgically removes the Windows Titlebar.
        """
        hwnd = self._get_hwnd(w)
        style = ctypes.windll.user32.GetWindowLongW(hwnd, self.GWL_STYLE)
        style = style & ~self.WS_CAPTION
        ctypes.windll.user32.SetWindowLongW(hwnd, self.GWL_STYLE, style)
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0020 | 0x0001 | 0x0002 | 0x0004 | 0x0010)

    def start_drag(self, w):
        hwnd = self._get_hwnd(w)
        ctypes.windll.user32.ReleaseCapture()
        ctypes.windll.user32.SendMessageW(hwnd, self.WM_NCLBUTTONDOWN, self.HTCAPTION, 0)

    def message_box(self, w, title, message, style=0):
        # style 0 = OK
        # style 1 = OK/Cancel
        # style 4 = Yes/No
        # Return: 1=OK, 2=Cancel, 6=Yes, 7=No
        hwnd = self._get_hwnd(w)
        return ctypes.windll.user32.MessageBoxW(hwnd, message, title, style)

    def set_window_icon(self, w, icon_path):
        if not icon_path: return
        hwnd = self._get_hwnd(w)
        
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        
        try:
            # Load Small Icon (16x16)
            h_icon_small = ctypes.windll.user32.LoadImageW(
                0, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
            )
            if h_icon_small:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)
                
            # Load Big Icon (32x32)
            h_icon_big = ctypes.windll.user32.LoadImageW(
                0, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE
            )
            if h_icon_big:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
        except Exception as e:
            print(f"Failed to set window icon: {e}")

    # --- New Daemon Capabilities ---

    SW_HIDE = 0
    SW_SHOW = 5
    NIM_ADD = 0
    NIM_MODIFY = 1
    NIM_DELETE = 2
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    NIF_INFO = 0x00000010
    szTip_MAX = 128
    szInfo_MAX = 256
    szInfoTitle_MAX = 64

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_uint),
            ("hWnd", ctypes.c_void_p),
            ("uID", ctypes.c_uint),
            ("uFlags", ctypes.c_uint),
            ("uCallbackMessage", ctypes.c_uint),
            ("hIcon", ctypes.c_void_p),
            ("szTip", ctypes.c_wchar * 128),
            ("dwState", ctypes.c_uint),
            ("dwStateMask", ctypes.c_uint),
            ("szInfo", ctypes.c_wchar * 256),
            ("uTimeout", ctypes.c_uint), # Union with uVersion
            ("szInfoTitle", ctypes.c_wchar * 64),
            ("dwInfoFlags", ctypes.c_uint),
            ("guidItem", ctypes.c_ubyte * 16), # GUID
            ("hBalloonIcon", ctypes.c_void_p),
        ]

    def hide(self, w):
        hwnd = self._get_hwnd(w)
        ctypes.windll.user32.ShowWindow(hwnd, self.SW_HIDE)

    def show(self, w):
        hwnd = self._get_hwnd(w)
        ctypes.windll.user32.ShowWindow(hwnd, self.SW_SHOW)
        ctypes.windll.user32.SetForegroundWindow(hwnd)

    def notification(self, w, title, message, icon=None):
        # Uses Shell_NotifyIcon with NIF_INFO for a balloon/toast notification
        try:
            nid = self.NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(self.NOTIFYICONDATAW)
            nid.uID = 1001 # Unique ID
            
            # Use the actual window handle so messages (and lifecycle) are attached to the app.
            # If w is None, we can't reliably show a notification that persists or handles clicks well.
            if w:
                 nid.hWnd = self._get_hwnd(w)
            else:
                 # Fallback, might fail on some Windows versions
                 nid.hWnd = 0
            
            nid.uFlags = self.NIF_INFO | self.NIF_TIP | self.NIF_ICON
            nid.dwInfoFlags = 1 # NIIF_INFO (Info icon)
            nid.szInfo = message[:255]
            nid.szInfoTitle = title[:63]
            nid.szTip = title[:127] # Tooltip
            
            # Try to load system icon (Application)
            # IDI_APPLICATION = 32512
            nid.hIcon = ctypes.windll.user32.LoadIconW(0, 32512) 
            
            res = ctypes.windll.shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(nid))
            
            # Remove it after a delay? Or the OS handles the balloon timeout.
            # But the icon remains. We technically should perform NIM_DELETE when app closes or after timeout.
            # For a pure "Notification" API, Windows requires a Tray Icon to anchor the balloon.
            # So we just added a tray icon.
            # A smarter implementation would check if we already have an icon.
            # For now, we leave it. Ideally, we should remove it on exit (webview_destroy handles window, but not icon).
            # We can implement a cleanup later or user manually removes.
            
        except Exception as e:
            print(f"Windows notification error: {e}")

    # --- File Dialogs Support ---

    class OPENFILENAMEW(ctypes.Structure):
        _fields_ = [
            ("lStructSize", ctypes.c_uint),
            ("hwndOwner", ctypes.c_void_p),
            ("hInstance", ctypes.c_void_p),
            ("lpstrFilter", ctypes.c_wchar_p),
            ("lpstrCustomFilter", ctypes.c_wchar_p),
            ("nMaxCustFilter", ctypes.c_uint),
            ("nFilterIndex", ctypes.c_uint),
            ("lpstrFile", ctypes.c_wchar_p),
            ("nMaxFile", ctypes.c_uint),
            ("lpstrFileTitle", ctypes.c_wchar_p),
            ("nMaxFileTitle", ctypes.c_uint),
            ("lpstrInitialDir", ctypes.c_wchar_p),
            ("lpstrTitle", ctypes.c_wchar_p),
            ("Flags", ctypes.c_uint),
            ("nFileOffset", ctypes.c_ushort),
            ("nFileExtension", ctypes.c_ushort),
            ("lpstrDefExt", ctypes.c_wchar_p),
            ("lCustData", ctypes.c_long),
            ("lpfnHook", ctypes.c_void_p),
            ("lpTemplateName", ctypes.c_wchar_p),
        ]

    # Flags
    OFN_EXPLORER = 0x00080000
    OFN_FILEMUSTEXIST = 0x00001000
    OFN_PATHMUSTEXIST = 0x00000800
    OFN_OVERWRITEPROMPT = 0x00000002
    OFN_NOCHANGEDIR = 0x00000008

    def _prepare_ofn(self, w, title, default_path, file_types, file_buffer_size=1024):
        ofn = self.OPENFILENAMEW()
        ofn.lStructSize = ctypes.sizeof(self.OPENFILENAMEW)
        ofn.hwndOwner = self._get_hwnd(w)
        
        # Buffer for file name
        buff = ctypes.create_unicode_buffer(file_buffer_size)
        ofn.lpstrFile = ctypes.addressof(buff)
        ofn.nMaxFile = file_buffer_size
        
        if title:
            ofn.lpstrTitle = title

        if default_path:
            # If default path is a file, set lpstrFile too ideally, but let's stick to dir
            # If it's just a dir, set InitialDir
            import os
            if os.path.isfile(default_path):
                 d = os.path.dirname(default_path)
                 n = os.path.basename(default_path)
                 ofn.lpstrInitialDir = d
                 buff.value = n
            else:
                 ofn.lpstrInitialDir = default_path
        
        # Filter format: "Desc\0*.ext\0Desc2\0*.ext2\0\0"
        # User input: "Desc (*.ext)|*.ext|Desc2 (*.opt)|*.opt"
        if not file_types:
            file_types = "All Files (*.*)|*.*"
            
        # Replace | with \0
        filter_str = file_types.replace("|", "\0") + "\0"
        ofn.lpstrFilter = filter_str
        
        return ofn, buff

    def open_file_dialog(self, w, title, default_path=None, file_types=None):
        ofn, buff = self._prepare_ofn(w, title, default_path, file_types)
        ofn.Flags = self.OFN_EXPLORER | self.OFN_FILEMUSTEXIST | self.OFN_PATHMUSTEXIST | self.OFN_NOCHANGEDIR
        
        if ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
            return buff.value
        return None

    def save_file_dialog(self, w, title, default_path=None, default_name=None, file_types=None):
        # Merge default_name into default_path logic if needed
        import os
        path = default_path
        if default_name:
             if path:
                 path = os.path.join(path, default_name)
             else:
                 path = default_name # Handled by _prepare (will treat as file if no abs path? logic in `_prepare` handles basename)
        
        ofn, buff = self._prepare_ofn(w, title, path, file_types)
        ofn.Flags = self.OFN_EXPLORER | self.OFN_OVERWRITEPROMPT | self.OFN_PATHMUSTEXIST | self.OFN_NOCHANGEDIR
        
        if ctypes.windll.comdlg32.GetSaveFileNameW(ctypes.byref(ofn)):
            return buff.value
        return None

    # Folder/Browse Logic using SHBrowseForFolder (Simple)
    class BROWSEINFOW(ctypes.Structure):
        _fields_ = [
            ("hwndOwner", ctypes.c_void_p),
            ("pidlRoot", ctypes.c_void_p),
            ("pszDisplayName", ctypes.c_wchar_p),
            ("lpszTitle", ctypes.c_wchar_p),
            ("ulFlags", ctypes.c_uint),
            ("lpfn", ctypes.c_void_p),
            ("lParam", ctypes.c_long),
            ("iImage", ctypes.c_int),
        ]
    BIF_RETURNONLYFSDIRS = 0x00000001
    BIF_NEWDIALOGSTYLE = 0x00000040

    def open_folder_dialog(self, w, title, default_path=None):
        bif = self.BROWSEINFOW()
        bif.hwndOwner = self._get_hwnd(w)
        bif.lpszTitle = title
        bif.ulFlags = self.BIF_RETURNONLYFSDIRS | self.BIF_NEWDIALOGSTYLE
        
        pidl = ctypes.windll.shell32.SHBrowseForFolderW(ctypes.byref(bif))
        if pidl:
            path = ctypes.create_unicode_buffer(260)
            if ctypes.windll.shell32.SHGetPathFromIDListW(pidl, path):
                ctypes.windll.shell32.ILFree(ctypes.c_void_p(pidl)) # Cleanup
                return path.value
            ctypes.windll.shell32.ILFree(ctypes.c_void_p(pidl))
        return None

    # --- Custom Protocol ---
    def register_protocol(self, scheme):
        import winreg
        import sys
        import os
        
        exe = sys.executable
        # If running from source (python.exe), we need to point to the script
        if not getattr(sys, 'frozen', False):
             # This is tricky for dev mode. Usually we point to python.exe + script
             # But let's assume for now we point to python.exe
             # A robust solution would forward arguments properly
             pass
        
        # Command: "path/to/exe" "%1"
        command = f'"{exe}" "%1"'
        
        try:
            # HKCU\Software\Classes\scheme
            key_path = f"Software\\Classes\\{scheme}"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"URL:{scheme} Protocol")
                winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
                
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{key_path}\\shell\\open\\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
                
            return True
        except Exception as e:
            print(f"Failed to register protocol: {e}")
            return False

    # --- Taskbar Progress (ITaskbarList3) ---
    # Simplified COM via ctypes without full comtypes dep
    
    TBPF_NOPROGRESS = 0
    TBPF_INDETERMINATE = 0x1
    TBPF_NORMAL = 0x2
    TBPF_ERROR = 0x4
    TBPF_PAUSED = 0x8
    
    _taskbar_list = None 
    
    def _init_taskbar(self):
        if self._taskbar_list: return self._taskbar_list
        try:
            # Initialize COM if needed (usually main thread is already init, but safe to check)
            try:
                ctypes.windll.ole32.CoInitialize(0)
            except: pass
            
            # ITaskbarList3 GUIDs
            CLSID_TaskbarList = "{56FDF344-FD6D-11d0-958A-006097C9A090}"
            IID_ITaskbarList3 = "{ea1afb91-9e28-4b86-90e9-9e9f8a5eefaf}"
            
            # We use a helper or just comtypes if available? 
            # User doesn't have comtypes in requirement list in pyproject.toml?
            # It's better to use 'comtypes' package if allowed, but to keep 'pytron-kit' dependency-light
            # we can try to do raw VTable access OR just recommend comtypes.
            # Actually, let's enable this ONLY if comtypes is installed to avoid crashes.
            import comtypes.client
            self._taskbar_list = comtypes.client.CreateObject(CLSID_TaskbarList, interface=comtypes.gen.TaskbarLib.ITaskbarList3)
            self._taskbar_list.HrInit()
            return self._taskbar_list
        except ImportError:
            # print("Taskbar progress requires 'comtypes' package.")
            return None
        except Exception as e:
            # print(f"Taskbar init failed: {e}")
            return None

    def set_taskbar_progress(self, w, state="normal", value=0, max_value=100):
        """
        state: 'none', 'indeterminate', 'normal', 'error', 'paused'
        """
        try:
            import comtypes # Check again
            tbl = self._init_taskbar()
            if not tbl: return
            
            hwnd = self._get_hwnd(w)
            
            flags = self.TBPF_NOPROGRESS
            if state == 'indeterminate': flags = self.TBPF_INDETERMINATE
            elif state == 'normal': flags = self.TBPF_NORMAL
            elif state == 'error': flags = self.TBPF_ERROR
            elif state == 'paused': flags = self.TBPF_PAUSED
            
            tbl.SetProgressState(hwnd, flags)
            
            if state in ('normal', 'error', 'paused'):
                tbl.SetProgressValue(hwnd, int(value), int(max_value))
                
        except Exception:
            pass

    def set_app_id(self, app_id):
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception as e:
            pass # AUMID setting might fail on older Windows or if already set
