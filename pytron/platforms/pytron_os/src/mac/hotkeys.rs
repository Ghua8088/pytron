/// macOS global hotkeys via Carbon EventHotKey API.
///
/// Modifiers are passed in Windows MOD_* format (1=Alt, 2=Ctrl, 4=Shift, 8=Win)
/// and translated to Carbon modifier masks.
/// Virtual-key codes are passed as Windows VK_* values and translated to
/// macOS HIToolbox key codes.
use pyo3::prelude::*;
use dashmap::DashMap;
use once_cell::sync::Lazy;
use std::os::raw::{c_int, c_uint, c_void};

// ─── Carbon FFI ──────────────────────────────────────────────────────────────

#[repr(C)]
struct EventHotKeyID {
    signature: u32,
    id: u32,
}

#[link(name = "Carbon", kind = "framework")]
extern "C" {
    fn GetApplicationEventTarget() -> *mut c_void;
    fn RegisterEventHotKey(
        key_code: c_uint,
        modifiers: c_uint,
        id: EventHotKeyID,
        target: *mut c_void,
        options: u32,
        out_ref: *mut *mut c_void,
    ) -> c_int;
    fn UnregisterEventHotKey(hotkey_ref: *mut c_void) -> c_int;
}

// ─── Global storage ──────────────────────────────────────────────────────────

static HOTKEY_REFS: Lazy<DashMap<i32, usize>> = Lazy::new(DashMap::new);

// ─── Helpers ─────────────────────────────────────────────────────────────────

/// Translate a Windows VK_* virtual-key code to a macOS HIToolbox key code.
fn vk_to_mac_keycode(vk: u32) -> Option<u32> {
    match vk {
        // Letters (VK_A–VK_Z = 0x41–0x5A)
        0x41 => Some(0),   0x42 => Some(11),  0x43 => Some(8),   0x44 => Some(2),
        0x45 => Some(14),  0x46 => Some(3),   0x47 => Some(5),   0x48 => Some(4),
        0x49 => Some(34),  0x4A => Some(38),  0x4B => Some(40),  0x4C => Some(37),
        0x4D => Some(46),  0x4E => Some(45),  0x4F => Some(31),  0x50 => Some(35),
        0x51 => Some(12),  0x52 => Some(15),  0x53 => Some(1),   0x54 => Some(17),
        0x55 => Some(32),  0x56 => Some(9),   0x57 => Some(13),  0x58 => Some(7),
        0x59 => Some(16),  0x5A => Some(6),
        // Digits (VK_0–VK_9 = 0x30–0x39)
        0x30 => Some(29),  0x31 => Some(18),  0x32 => Some(19),  0x33 => Some(20),
        0x34 => Some(21),  0x35 => Some(23),  0x36 => Some(22),  0x37 => Some(26),
        0x38 => Some(28),  0x39 => Some(25),
        // Function keys (VK_F1–VK_F12 = 0x70–0x7B)
        0x70 => Some(122), 0x71 => Some(120), 0x72 => Some(99),  0x73 => Some(118),
        0x74 => Some(96),  0x75 => Some(97),  0x76 => Some(98),  0x77 => Some(100),
        0x78 => Some(101), 0x79 => Some(109), 0x7A => Some(103), 0x7B => Some(111),
        // Common keys
        0x1B => Some(53),  // Escape
        0x0D => Some(36),  // Enter/Return
        0x08 => Some(51),  // Backspace
        0x09 => Some(48),  // Tab
        0x20 => Some(49),  // Space
        0x25 => Some(123), // Left Arrow
        0x26 => Some(126), // Up Arrow
        0x27 => Some(124), // Right Arrow
        0x28 => Some(125), // Down Arrow
        _ => None,
    }
}

/// Translate Windows MOD_* flags to Carbon modifier masks.
fn win_mod_to_carbon(modifiers: u32) -> u32 {
    let mut m = 0u32;
    if modifiers & 1 != 0 { m |= 0x0800; } // MOD_ALT   → optionKey
    if modifiers & 2 != 0 { m |= 0x0100; } // MOD_CTRL  → cmdKey
    if modifiers & 4 != 0 { m |= 0x0200; } // MOD_SHIFT → shiftKey
    if modifiers & 8 != 0 { m |= 0x1000; } // MOD_WIN   → controlKey
    m
}

// ─── Public API ──────────────────────────────────────────────────────────────

#[pyfunction]
pub fn register_hotkey(_hwnd_val: usize, id: i32, modifiers: u32, vk: u32) -> PyResult<bool> {
    let Some(mac_vk) = vk_to_mac_keycode(vk) else { return Ok(false) };
    let mac_mod = win_mod_to_carbon(modifiers);
    let hk_id   = EventHotKeyID { signature: u32::from_be_bytes(*b"pytR"), id: id as u32 };
    let mut hk_ref: *mut c_void = std::ptr::null_mut();
    let target = unsafe { GetApplicationEventTarget() };
    let err = unsafe { RegisterEventHotKey(mac_vk, mac_mod, hk_id, target, 0, &mut hk_ref) };
    if err == 0 && !hk_ref.is_null() {
        HOTKEY_REFS.insert(id, hk_ref as usize);
        Ok(true)
    } else {
        Ok(false)
    }
}

#[pyfunction]
pub fn unregister_hotkey(_hwnd_val: usize, id: i32) -> PyResult<bool> {
    if let Some((_, ptr)) = HOTKEY_REFS.remove(&id) {
        let err = unsafe { UnregisterEventHotKey(ptr as *mut c_void) };
        Ok(err == 0)
    } else {
        Ok(false)
    }
}
