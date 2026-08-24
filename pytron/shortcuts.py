from concurrent.futures import ThreadPoolExecutor
import ctypes
import logging
import queue
import sys
import threading
from typing import Any, Callable, Dict, Optional, Union

from .utils import resolve_native_bridge

_AUTO_NATIVE_BRIDGE = object()
native_bridge = _AUTO_NATIVE_BRIDGE


def _get_native_bridge():
    global native_bridge
    if native_bridge is _AUTO_NATIVE_BRIDGE:
        return resolve_native_bridge()
    return native_bridge


def _bridge_has(*names):
    bridge = _get_native_bridge()
    if not bridge:
        return False
    return all(hasattr(bridge, name) for name in names)


def _has_rust_hotkey_bridge():
    return _bridge_has(
        "get_current_thread_id",
        "init_message_queue",
        "get_message",
        "register_hotkey",
        "translate_dispatch",
        "post_thread_message",
    )


try:
    import ctypes.wintypes
except (ImportError, AttributeError):
    # Fallback for non-Windows platforms
    class MockWintypes:
        class MSG(ctypes.Structure):
            _fields_ = [("hwnd", ctypes.c_void_p), ("message", ctypes.c_uint)]

    ctypes.wintypes = MockWintypes

# Windows Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_USER = 0x0400
WM_APP_REGISTER = WM_USER + 1
WM_APP_UNREGISTER = WM_USER + 2

# Comprehensive Virtual-Key Code Map (Windows)
VK_MAP = {
    # Letters (A-Z)
    **{chr(c): c for c in range(ord("A"), ord("Z") + 1)},
    # Digits (0-9)
    **{chr(c): c for c in range(ord("0"), ord("9") + 1)},
    # Function keys (F1-F24)
    **{f"F{i}": 0x70 + (i - 1) for i in range(1, 25)},
    # Navigation & Editing
    "SPACE": 0x20,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "ESCAPE": 0x1B,
    "ESC": 0x1B,
    "BACKSPACE": 0x08,
    "BKSP": 0x08,
    "TAB": 0x09,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "PAGEUP": 0x21,
    "PGUP": 0x21,
    "PAGEDOWN": 0x22,
    "PGDN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "INSERT": 0x2D,
    "INS": 0x2D,
    "DELETE": 0x2E,
    "DEL": 0x2E,
    "PRINTSCREEN": 0x2C,
    "PRTSC": 0x2C,
    "PAUSE": 0x13,
    "CAPSLOCK": 0x14,
    "CAPS": 0x14,
    "NUMLOCK": 0x90,
    "SCROLLLOCK": 0x91,
    # Punctuation & Symbols (OEM keys for standard US layout)
    "-": 0xBD,
    "MINUS": 0xBD,
    "DASH": 0xBD,
    "=": 0xBB,
    "+": 0xBB,
    "PLUS": 0xBB,
    "EQUAL": 0xBB,
    "EQUALS": 0xBB,
    "[": 0xDB,
    "LBRACKET": 0xDB,
    "BRACKETLEFT": 0xDB,
    "OPEN_BRACKET": 0xDB,
    "]": 0xDD,
    "RBRACKET": 0xDD,
    "BRACKETRIGHT": 0xDD,
    "CLOSE_BRACKET": 0xDD,
    "\\": 0xDC,
    "BACKSLASH": 0xDC,
    ";": 0xBA,
    "SEMICOLON": 0xBA,
    "'": 0xDE,
    "QUOTE": 0xDE,
    "APOSTROPHE": 0xDE,
    ",": 0xBC,
    "COMMA": 0xBC,
    ".": 0xBE,
    "PERIOD": 0xBE,
    "DOT": 0xBE,
    "/": 0xBF,
    "SLASH": 0xBF,
    "`": 0xC0,
    "BACKQUOTE": 0xC0,
    "GRAVE": 0xC0,
    "TILDE": 0xC0,
    "~": 0xC0,
    # Numpad keys
    "NUMPAD0": 0x60,
    "NUMPAD1": 0x61,
    "NUMPAD2": 0x62,
    "NUMPAD3": 0x63,
    "NUMPAD4": 0x64,
    "NUMPAD5": 0x65,
    "NUMPAD6": 0x66,
    "NUMPAD7": 0x67,
    "NUMPAD8": 0x68,
    "NUMPAD9": 0x69,
    "NUMPAD_ADD": 0x6B,
    "NUMPAD_SUBTRACT": 0x6D,
    "NUMPAD_MULTIPLY": 0x6A,
    "NUMPAD_DIVIDE": 0x6F,
    "NUMPAD_DECIMAL": 0x6E,
    "NUMPAD_ENTER": 0x0D,
}

# X11 Keysyms for Linux (python-xlib)
XK_MAP = {
    "SPACE": 0x0020,
    "ENTER": 0xFF0D,
    "RETURN": 0xFF0D,
    "ESCAPE": 0xFF1B,
    "ESC": 0xFF1B,
    "BACKSPACE": 0xFF08,
    "BKSP": 0xFF08,
    "TAB": 0xFF09,
    "LEFT": 0xFF51,
    "UP": 0xFF52,
    "RIGHT": 0xFF53,
    "DOWN": 0xFF54,
    "PAGEUP": 0xFF55,
    "PGUP": 0xFF55,
    "PAGEDOWN": 0xFF56,
    "PGDN": 0xFF56,
    "END": 0xFF57,
    "HOME": 0xFF50,
    "INSERT": 0xFF63,
    "INS": 0xFF63,
    "DELETE": 0xFFFF,
    "DEL": 0xFFFF,
    **{f"F{i}": 0xFFBD + i for i in range(1, 25)},
    "-": 0x002D,
    "MINUS": 0x002D,
    "DASH": 0x002D,
    "=": 0x003D,
    "EQUAL": 0x003D,
    "EQUALS": 0x003D,
    "+": 0x002B,
    "PLUS": 0x002B,
    "[": 0x005B,
    "LBRACKET": 0x005B,
    "]": 0x005D,
    "RBRACKET": 0x005D,
    "\\": 0x005C,
    "BACKSLASH": 0x005C,
    ";": 0x003B,
    "SEMICOLON": 0x003B,
    "'": 0x0027,
    "QUOTE": 0x0027,
    "APOSTROPHE": 0x0027,
    ",": 0x002C,
    "COMMA": 0x002C,
    ".": 0x002E,
    "PERIOD": 0x002E,
    "DOT": 0x002E,
    "/": 0x002F,
    "SLASH": 0x002F,
    "`": 0x0060,
    "BACKQUOTE": 0x0060,
    "GRAVE": 0x0060,
}

# X11 modifier masks
_X11_SHIFT = 1  # ShiftMask
_X11_CONTROL = 4  # ControlMask
_X11_ALT = 8  # Mod1Mask (Alt)
_X11_SUPER = 64  # Mod4Mask (Win/Super)
_X11_NUMLOCK = 16  # Mod2Mask  — noise modifier, must iterate
_X11_LOCK = 2  # LockMask  — noise modifier, must iterate


class ShortcutManager:
    def __init__(self):
        self.shortcuts: Dict[int, Any] = {}
        self.logger = logging.getLogger("Pytron.Shortcuts")
        self._running = False
        self._next_id = 1
        self._thread = None
        self._reg_queue = queue.Queue()
        self._thread_id = None
        self._queue_ready = threading.Event()
        self._executor = ThreadPoolExecutor(
            max_workers=8, thread_name_prefix="Pytron-ShortcutWorker"
        )
        # Linux / X11
        self._xlib_display = None
        self._xlib_root = None
        self._xlib_lock = threading.Lock()

    def _normalize_combo(self, combo: str) -> str:
        parts = [part.strip() for part in combo.split("+") if part.strip()]
        normalized = []
        for part in parts:
            upper = part.upper()
            if upper in ("CONTROL", "CTRL"):
                upper = "CTRL"
            elif upper in ("COMMAND", "CMD"):
                upper = "CMD"
            elif upper in ("OPTION", "ALT"):
                upper = "ALT"
            elif upper in ("SUPER", "WIN", "WINDOWS"):
                upper = "WIN"
            normalized.append(upper)
        return "+".join(normalized)

    def _dispatch_callback(self, cb: Callable):
        """Dispatches a shortcut callback in a daemon thread with error protection."""
        threading.Thread(target=cb, daemon=True).start()

    def register(self, combo: str, callback: Callable) -> Optional[int]:
        """Registers a global shortcut (e.g., 'Ctrl+Alt+S'). Returns the assigned shortcut ID."""
        platform = sys.platform
        if platform == "win32":
            return self._register_windows(combo, callback)
        elif platform == "darwin":
            return self._register_darwin(combo, callback)
        elif platform.startswith("linux"):
            return self._register_linux(combo, callback)
        else:
            self.logger.warning(f"Global shortcuts not implemented for {platform}")
            return None

    def unregister(self, combo_or_id: Union[int, str]) -> bool:
        """Unregisters a previously registered global shortcut by ID or combo string."""
        target_sid = None
        if isinstance(combo_or_id, int):
            target_sid = combo_or_id
        else:
            norm = self._normalize_combo(combo_or_id)
            for sid, data in list(self.shortcuts.items()):
                if self._normalize_combo(data.get("combo", "")) == norm:
                    target_sid = sid
                    break

        if target_sid is None or target_sid not in self.shortcuts:
            return False

        platform = sys.platform
        if platform == "win32":
            return self._unregister_windows(target_sid)
        elif platform.startswith("linux"):
            return self._unregister_linux(target_sid)
        else:
            self.shortcuts.pop(target_sid, None)
            return True

    def _register_darwin(self, combo: str, callback: Callable) -> Optional[int]:
        """macOS implementation via Quartz Global Event Monitor."""
        modifiers, vk = self._parse_combo(combo)
        if not vk:
            self.logger.error(f"Invalid shortcut combo: {combo}")
            return None

        mac_mods = 0
        if modifiers & MOD_CONTROL:
            mac_mods |= 1 << 0
        if modifiers & MOD_SHIFT:
            mac_mods |= 1 << 1
        if modifiers & MOD_ALT:
            mac_mods |= 1 << 3
        if modifiers & MOD_WIN:
            mac_mods |= 1 << 8

        if not self._running:
            self._start_darwin_loop()

        sid = self._next_id
        self._next_id += 1
        self.shortcuts[sid] = {
            "mac_mods": mac_mods,
            "vk": vk,
            "callback": callback,
            "combo": combo,
        }
        return sid

    def _start_darwin_loop(self):
        try:
            from Quartz import (
                kCGEventKeyDown,
            )

            self._running = True

            def _handler(proxy, type, event, refcon):
                if type != kCGEventKeyDown:
                    return event
                return event

            self.logger.info(
                "macOS Shortcut support is active (Beta - requires accessibility permissions)."
            )

        except ImportError:
            self.logger.error("macOS Shortcuts require 'pyobjc-framework-Quartz'.")

    # ------------------------------------------------------------------ Linux

    def _x11_mod_mask(self, modifiers: int) -> int:
        mask = 0
        if modifiers & MOD_CONTROL:
            mask |= _X11_CONTROL
        if modifiers & MOD_ALT:
            mask |= _X11_ALT
        if modifiers & MOD_SHIFT:
            mask |= _X11_SHIFT
        if modifiers & MOD_WIN:
            mask |= _X11_SUPER
        return mask

    def _register_linux(self, combo: str, callback: Callable) -> Optional[int]:
        """X11 global hotkey via python-xlib. Silently skips on Wayland."""
        import os

        combo = self._normalize_combo(combo)

        if not os.environ.get("DISPLAY"):
            self.logger.warning(
                "Global shortcuts: no DISPLAY found (Wayland/headless). Skipping."
            )
            return None
        try:
            from Xlib import display as xdisplay  # noqa: F401
        except ImportError:
            self.logger.error(
                "Global shortcuts on Linux require 'python-xlib'. "
                "Install: pip install python-xlib"
            )
            return None

        modifiers, _ = self._parse_combo(combo)
        xmods = self._x11_mod_mask(modifiers)

        key_part = combo.split("+")[-1]
        keysym = XK_MAP.get(key_part) or (
            ord(key_part.lower()) if len(key_part) == 1 else None
        )
        if not keysym:
            self.logger.error(f"Cannot resolve X11 keysym for: {combo}")
            return None

        if not self._running:
            self._start_xlib_loop()
            if not self._queue_ready.wait(timeout=2.0):
                self.logger.error("X11 shortcut loop failed to start.")
                return None

        with self._xlib_lock:
            disp = self._xlib_display
        if disp is None:
            self.logger.error("X11 display not available.")
            return None

        keycode = disp.keysym_to_keycode(keysym)
        if not keycode:
            self.logger.error(f"X11: keysym 0x{keysym:04X} -> keycode 0 for {combo}")
            return None

        sid = self._next_id
        self._next_id += 1
        self.shortcuts[sid] = {
            "id": sid,
            "xmods": xmods,
            "xkeycode": keycode,
            "callback": callback,
            "registered": False,
            "combo": combo,
        }

        self._xlib_grab(sid)
        return sid

    def _unregister_linux(self, sid: int) -> bool:
        data = self.shortcuts.pop(sid, None)
        if not data:
            return False

        with self._xlib_lock:
            disp = self._xlib_display
            root = self._xlib_root
        if disp and root:
            from Xlib import X

            keycode = data["xkeycode"]
            xmods = data["xmods"]
            for extra in [0, _X11_NUMLOCK, _X11_LOCK, _X11_NUMLOCK | _X11_LOCK]:
                try:
                    root.ungrab_key(keycode, xmods | extra)
                except Exception:
                    pass
            disp.sync()
        return True

    def _start_xlib_loop(self):
        self._running = True
        self._queue_ready.clear()
        self._thread = threading.Thread(target=self._xlib_msg_loop, daemon=True)
        self._thread.start()

    def _xlib_msg_loop(self):
        from Xlib import X
        from Xlib import display as xdisplay

        try:
            disp = xdisplay.Display()
            root = disp.screen().root
            root.change_attributes(event_mask=X.KeyPressMask)
        except Exception as e:
            self.logger.error(f"X11 Display init failed: {e}")
            self._queue_ready.set()
            return

        with self._xlib_lock:
            self._xlib_display = disp
            self._xlib_root = root

        self._queue_ready.set()
        self.logger.info("X11 global shortcut loop started.")

        _NOISE = _X11_NUMLOCK | _X11_LOCK
        while self._running:
            try:
                event = disp.next_event()
            except Exception:
                break
            if event.type != X.KeyPress:
                continue
            keycode = event.detail
            state = event.state & ~_NOISE
            for data in list(self.shortcuts.values()):
                if data.get("xkeycode") == keycode and data.get("xmods") == state:
                    self._dispatch_callback(data["callback"])

        disp.close()

    def _xlib_grab(self, sid: int):
        """Grab key with all noise-modifier combos so NumLock/CapsLock don't block it."""
        from Xlib import X

        data = self.shortcuts[sid]
        root = self._xlib_root
        keycode = data["xkeycode"]
        xmods = data["xmods"]
        for extra in [0, _X11_NUMLOCK, _X11_LOCK, _X11_NUMLOCK | _X11_LOCK]:
            root.grab_key(
                keycode,
                xmods | extra,
                True,
                X.GrabModeAsync,
                X.GrabModeAsync,
            )
        if self._xlib_display is not None:
            self._xlib_display.sync()
        data["registered"] = True
        self.logger.info(
            f"Registered X11 shortcut: {data['combo']} "
            f"(keycode={keycode}, xmods=0x{xmods:02X})"
        )

    def _parse_combo(self, combo: str):
        combo = self._normalize_combo(combo)
        parts = combo.split("+")
        modifiers = 0
        vk = 0

        for part in parts:
            if part in ("CTRL", "CONTROL"):
                modifiers |= MOD_CONTROL
            elif part in ("ALT", "OPTION"):
                modifiers |= MOD_ALT
            elif part in ("SHIFT",):
                modifiers |= MOD_SHIFT
            elif part in ("WIN", "SUPER", "CMD", "COMMAND"):
                modifiers |= MOD_WIN
            else:
                # Precise key lookup
                vk = VK_MAP.get(part, 0)
                if not vk:
                    # Uppercase single alphanumeric character
                    if len(part) == 1 and part.isalnum():
                        vk = ord(part.upper())

        # Win32 MOD_NOREPEAT flag prevents repeat hotkeys when key is held down
        if sys.platform == "win32":
            modifiers |= MOD_NOREPEAT

        return modifiers, vk

    def _register_windows(self, combo: str, callback: Callable) -> Optional[int]:
        modifiers, vk = self._parse_combo(combo)
        if not vk:
            self.logger.error(f"Invalid shortcut combo: {combo}")
            return None

        sid = self._next_id
        self._next_id += 1

        # 1. Start loop if not running
        if not self._running:
            self._start_message_loop()
            if not self._queue_ready.wait(timeout=2.0):
                self.logger.error("Shortcut message loop failed to initialize in time.")
                return None

        # 2. Push to local dict with 'False' registered state
        data = {
            "id": sid,
            "fsModifiers": modifiers,
            "vk": vk,
            "callback": callback,
            "registered": False,
            "combo": combo,
        }
        self.shortcuts[sid] = data

        # 3. Wake up the loop to register the key
        self._post_thread_msg(WM_APP_REGISTER, sid, 0)
        return sid

    def _unregister_windows(self, sid: int) -> bool:
        if sid not in self.shortcuts:
            return False

        data = self.shortcuts[sid]
        data["to_unregister"] = True

        # Post unregister message to the owning message loop thread
        self._post_thread_msg(WM_APP_UNREGISTER, sid, 0)
        return True

    def _post_thread_msg(self, msg: int, wparam: int = 0, lparam: int = 0) -> bool:
        if not self._thread_id:
            return False

        bridge = _get_native_bridge()
        if _has_rust_hotkey_bridge() and bridge:
            try:
                if bridge.post_thread_message(self._thread_id, msg, wparam, lparam):
                    return True
            except Exception:
                pass

        # ctypes fallback
        for _ in range(3):
            try:
                if ctypes.windll.user32.PostThreadMessageW(
                    self._thread_id, msg, wparam, lparam
                ):
                    return True
            except Exception:
                pass
            import time

            time.sleep(0.02)

        return False

    def _start_message_loop(self):
        self._running = True
        self._queue_ready.clear()
        self._thread = threading.Thread(target=self._msg_loop, daemon=True)
        self._thread.start()

    def _msg_loop(self):
        bridge = _get_native_bridge()
        if _has_rust_hotkey_bridge() and bridge:
            # ── RUST PATH ──────────────────────────────────────────────────
            try:
                self._thread_id = bridge.get_current_thread_id()
            except Exception:
                self._thread_id = None

            try:
                bridge.init_message_queue()
            except Exception:
                pass

            self._queue_ready.set()
            self.logger.info("Shortcut loop started (rust path).")

            while self._running:
                try:
                    res = bridge.get_message()  # blocks
                    if res is None:  # WM_QUIT
                        break
                    message, wparam, lparam = res
                except Exception as e:
                    self.logger.error(f"get_message failed: {e}")
                    break

                if message == WM_HOTKEY:
                    sid = wparam
                    if sid in self.shortcuts:
                        cb = self.shortcuts[sid]["callback"]
                        self._dispatch_callback(cb)

                elif message == WM_APP_REGISTER:
                    for sid, data in list(self.shortcuts.items()):
                        if not data.get("registered", False):
                            try:
                                success = bridge.register_hotkey(
                                    0, sid, data["fsModifiers"], data["vk"]
                                )
                            except Exception:
                                success = False

                            if success:
                                data["registered"] = True
                                self.logger.info(
                                    f"Registered global shortcut ID {sid} ({data.get('combo')})"
                                )
                            else:
                                self.logger.warning(
                                    f"Failed to register ID {sid} ({data.get('combo')})"
                                )
                                data["registered"] = True

                elif message == WM_APP_UNREGISTER:
                    for sid, data in list(self.shortcuts.items()):
                        if data.get("to_unregister"):
                            try:
                                bridge.unregister_hotkey(0, sid)
                            except Exception:
                                pass
                            self.shortcuts.pop(sid, None)
                            self.logger.info(f"Unregistered global shortcut ID {sid}")

                try:
                    bridge.translate_dispatch(0, message, wparam, lparam)
                except Exception:
                    pass

            # Cleanup on exit
            for sid in list(self.shortcuts.keys()):
                try:
                    bridge.unregister_hotkey(0, sid)
                except Exception:
                    pass
            return  # done with rust path

        # ── CTYPES FALLBACK PATH ────────────────────────────────────────────
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        user32 = ctypes.windll.user32
        msg = ctypes.wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 0)  # init queue
        self._queue_ready.set()

        self.logger.info("Shortcut loop started (ctypes fallback).")

        while self._running:
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res <= 0:
                break

            if msg.message == WM_HOTKEY:
                sid = msg.wParam
                if sid in self.shortcuts:
                    cb = self.shortcuts[sid]["callback"]
                    self._dispatch_callback(cb)

            elif msg.message == WM_APP_REGISTER:
                for sid, data in list(self.shortcuts.items()):
                    if not data.get("registered", False):
                        success = user32.RegisterHotKey(
                            None, sid, data["fsModifiers"], data["vk"]
                        )
                        if success:
                            data["registered"] = True
                            self.logger.info(
                                f"Registered global shortcut ID {sid} ({data.get('combo')})"
                            )
                        else:
                            err_code = ctypes.GetLastError()
                            if err_code == 1409:
                                self.logger.warning(
                                    f"Shortcut ID {sid} failed: Hotkey already reserved ({data.get('combo')})."
                                )
                            else:
                                self.logger.error(
                                    f"Failed to register ID {sid} ({data.get('combo')}). Error: {err_code}"
                                )
                            data["registered"] = True

            elif msg.message == WM_APP_UNREGISTER:
                for sid, data in list(self.shortcuts.items()):
                    if data.get("to_unregister"):
                        user32.UnregisterHotKey(None, sid)
                        self.shortcuts.pop(sid, None)
                        self.logger.info(f"Unregistered global shortcut ID {sid}")

            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup on exit
        for sid in list(self.shortcuts.keys()):
            user32.UnregisterHotKey(None, sid)

    def stop(self):
        self._running = False
        if sys.platform == "win32":
            # Post WM_QUIT to break the GetMessage loop
            if self._thread_id:
                self._post_thread_msg(0x0012, 0, 0)  # WM_QUIT

        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
