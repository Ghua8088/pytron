/// Linux global hotkeys via Xlib XGrabKey.
///
/// Modifiers follow the Windows MOD_* convention (1=Alt, 2=Ctrl, 4=Shift, 8=Super)
/// and are translated to X11 modifier masks.
/// Virtual-key codes follow Windows VK_* and are translated to X11 KeySyms.
use pyo3::prelude::*;
use dashmap::DashMap;
use once_cell::sync::Lazy;
use std::os::raw::{c_char, c_int, c_uchar, c_uint, c_ulong, c_void};

// ─── Xlib FFI ─────────────────────────────────────────────────────────────────

extern "C" {
    fn XOpenDisplay(display: *const c_char) -> *mut c_void;
    fn XCloseDisplay(display: *mut c_void) -> c_int;
    fn XDefaultRootWindow(display: *mut c_void) -> c_ulong;
    fn XGrabKey(
        display: *mut c_void,
        keycode: c_int,
        modifiers: c_uint,
        grab_window: c_ulong,
        owner_events: c_int,
        pointer_mode: c_int,
        keyboard_mode: c_int,
    ) -> c_int;
    fn XUngrabKey(
        display: *mut c_void,
        keycode: c_int,
        modifiers: c_uint,
        grab_window: c_ulong,
    ) -> c_int;
    fn XKeysymToKeycode(display: *mut c_void, keysym: c_ulong) -> c_uchar;
    fn XFlush(display: *mut c_void) -> c_int;
}

// ─── Global display handle ───────────────────────────────────────────────────

struct Display(*mut c_void);
unsafe impl Send for Display {}
unsafe impl Sync for Display {}

static DISPLAY: Lazy<Option<Display>> = Lazy::new(|| {
    let d = unsafe { XOpenDisplay(std::ptr::null()) };
    if d.is_null() { None } else { Some(Display(d)) }
});

fn get_display() -> Option<*mut c_void> {
    DISPLAY.as_ref().map(|d| d.0)
}

// Registered hotkeys: id → (keycode, modifiers)
static HOTKEYS: Lazy<DashMap<i32, (c_int, c_uint)>> = Lazy::new(DashMap::new);

// ─── Translation helpers ──────────────────────────────────────────────────────

/// Windows VK_* → X11 KeySym
fn vk_to_keysym(vk: u32) -> Option<c_ulong> {
    match vk {
        // Letters: VK_A–VK_Z = 0x41–0x5A, X11 uses lowercase a–z = 97–122
        0x41..=0x5A => Some((vk + 32) as c_ulong),
        // Digits: same values
        0x30..=0x39 => Some(vk as c_ulong),
        // Function keys: XK_F1–F12 = 0xFFBE–0xFFC9
        0x70..=0x7B => Some((0xFFBE + (vk - 0x70)) as c_ulong),
        // Common keys
        0x1B => Some(0xFF1B), // Escape
        0x0D => Some(0xFF0D), // Return
        0x08 => Some(0xFF08), // BackSpace
        0x09 => Some(0xFF09), // Tab
        0x20 => Some(0x0020), // Space
        0x25 => Some(0xFF51), // Left
        0x26 => Some(0xFF52), // Up
        0x27 => Some(0xFF53), // Right
        0x28 => Some(0xFF54), // Down
        _ => None,
    }
}

/// Windows MOD_* → X11 modifier mask
fn win_mod_to_x11(modifiers: u32) -> c_uint {
    let mut m: c_uint = 0;
    if modifiers & 1 != 0 { m |= 8; }   // MOD_ALT   → Mod1Mask
    if modifiers & 2 != 0 { m |= 4; }   // MOD_CTRL  → ControlMask
    if modifiers & 4 != 0 { m |= 1; }   // MOD_SHIFT → ShiftMask
    if modifiers & 8 != 0 { m |= 64; }  // MOD_WIN   → Mod4Mask (Super)
    m
}

// GrabMode constants
const GRAB_MODE_ASYNC: c_int = 1;

// ─── Public API ───────────────────────────────────────────────────────────────

#[pyfunction]
pub fn register_hotkey(_hwnd_val: usize, id: i32, modifiers: u32, vk: u32) -> PyResult<bool> {
    let Some(display) = get_display() else { return Ok(false) };
    let Some(sym) = vk_to_keysym(vk) else { return Ok(false) };
    let x_mod = win_mod_to_x11(modifiers);
    let root   = unsafe { XDefaultRootWindow(display) };
    let kc     = unsafe { XKeysymToKeycode(display, sym) };
    if kc == 0 { return Ok(false) }
    let res = unsafe {
        XGrabKey(display, kc as c_int, x_mod, root, 0, GRAB_MODE_ASYNC, GRAB_MODE_ASYNC)
    };
    if res != 0 {
        unsafe { XFlush(display); }
        HOTKEYS.insert(id, (kc as c_int, x_mod));
        Ok(true)
    } else {
        Ok(false)
    }
}

#[pyfunction]
pub fn unregister_hotkey(_hwnd_val: usize, id: i32) -> PyResult<bool> {
    let Some(display) = get_display() else { return Ok(false) };
    if let Some((_, (kc, mod_mask))) = HOTKEYS.remove(&id) {
        let root = unsafe { XDefaultRootWindow(display) };
        let res  = unsafe { XUngrabKey(display, kc, mod_mask, root) };
        unsafe { XFlush(display); }
        Ok(res != 0)
    } else {
        Ok(false)
    }
}
