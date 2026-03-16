use pyo3::prelude::*;
use windows::Win32::Foundation::HWND;
use windows::Win32::UI::Input::KeyboardAndMouse::{RegisterHotKey, UnregisterHotKey, HOT_KEY_MODIFIERS};

#[pyfunction]
pub fn register_hotkey(hwnd_val: usize, id: i32, modifiers: u32, vk: u32) -> PyResult<bool> {
    let hwnd = HWND(hwnd_val as isize);
    unsafe { Ok(RegisterHotKey(hwnd, id, HOT_KEY_MODIFIERS(modifiers), vk).is_ok()) }
}

#[pyfunction]
pub fn unregister_hotkey(hwnd_val: usize, id: i32) -> PyResult<bool> {
    let hwnd = HWND(hwnd_val as isize);
    unsafe { Ok(UnregisterHotKey(hwnd, id).is_ok()) }
}
