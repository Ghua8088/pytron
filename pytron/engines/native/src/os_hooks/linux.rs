use pyo3::prelude::*;
use pyo3::PyObject;
use rfd::FileDialog;
use arboard::Clipboard;
use notify_rust::Notification;

#[pyfunction]
pub fn message_box(
    _py: Python<'_>,
    hwnd_val: usize,
    title: String,
    message: String,
    level: String,
) -> PyResult<i32> {
    println!("[Linux] Message Box: {} - {}", title, message);
    Ok(1) // IDOK
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, default_path=None, _file_types=None))]
pub fn open_file_dialog(
    _py: Python<'_>,
    hwnd_val: usize,
    title: String,
    default_path: Option<String>,
    _file_types: Option<PyObject>,
) -> PyResult<Option<String>> {
    let mut dialog = FileDialog::new().set_title(&title);
    if let Some(path) = default_path {
        dialog = dialog.set_directory(path);
    }
    let file = dialog.pick_file();
    Ok(file.map(|p| p.to_string_lossy().to_string()))
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, default_path=None, default_name=None, _file_types=None))]
pub fn save_file_dialog(
    _py: Python<'_>,
    hwnd_val: usize,
    title: String,
    default_path: Option<String>,
    default_name: Option<String>,
    _file_types: Option<PyObject>,
) -> PyResult<Option<String>> {
    let mut dialog = FileDialog::new().set_title(&title);
    if let Some(path) = default_path {
        dialog = dialog.set_directory(path);
    }
    if let Some(name) = default_name {
        dialog = dialog.set_file_name(name);
    }
    let file = dialog.save_file();
    Ok(file.map(|p| p.to_string_lossy().to_string()))
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, default_path=None))]
pub fn open_folder_dialog(
    _py: Python<'_>,
    hwnd_val: usize,
    title: String,
    default_path: Option<String>,
) -> PyResult<Option<String>> {
    let mut dialog = FileDialog::new().set_title(&title);
    if let Some(path) = default_path {
        dialog = dialog.set_directory(path);
    }
    let folder = dialog.pick_folder();
    Ok(folder.map(|p| p.to_string_lossy().to_string()))
}

#[pyfunction]
pub fn set_clipboard_text(text: String) -> PyResult<bool> {
    if let Ok(mut clipboard) = Clipboard::new() {
        let _ = clipboard.set_text(text);
        Ok(true)
    } else {
        Ok(false)
    }
}

#[pyfunction]
pub fn get_clipboard_text() -> PyResult<Option<String>> {
    if let Ok(mut clipboard) = Clipboard::new() {
        Ok(clipboard.get_text().ok())
    } else {
        Ok(None)
    }
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, message, icon_path=None))]
pub fn show_notification(hwnd_val: usize, title: String, message: String, icon_path: Option<String>) -> PyResult<()> {
    let _ = Notification::new()
        .summary(&title)
        .body(&message)
        .show();
    Ok(())
}

// Stubs for Windows-only features to keep the pymodule block happy
#[pyfunction] pub fn minimize(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn maximize(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn restore(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn set_title(_h: usize, _t: String) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn show(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn hide(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn close(_h: usize) -> PyResult<()> { Ok(()) }

#[pyfunction]
#[pyo3(signature = (hwnd_val, x, y, width, height, no_move=None, no_size=None))]
pub fn set_bounds(
    hwnd_val: usize,
    x: i32,
    y: i32,
    width: i32,
    height: i32,
    no_move: Option<bool>,
    no_size: Option<bool>,
) -> PyResult<()> {
    Ok(())
}

#[pyfunction] pub fn toggle_maximize(_h: usize) -> PyResult<bool> { Ok(false) }
#[pyfunction] pub fn set_always_on_top(_h: usize, _e: bool) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn start_drag(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn is_visible(_h: usize) -> PyResult<bool> { Ok(true) }

#[pyfunction]
#[pyo3(signature = (hwnd_val, width=None, height=None))]
pub fn center(hwnd_val: usize, width: Option<i32>, height: Option<i32>) -> PyResult<()> {
    Ok(())
}

#[pyfunction] pub fn set_border_color(_h: usize, _c: u32) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn set_window_icon(_h: usize, _p: String) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn set_fullscreen(_h: usize, _e: bool) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn set_app_id(_id: String) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn set_launch_on_boot(_n: String, _p: String, _e: bool) -> PyResult<bool> { Ok(true) }
#[pyfunction] pub fn set_taskbar_progress(_h: usize, _s: String, _v: u64, _m: u64) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn set_utility_window(_h: usize, _e: bool) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn make_frameless(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn register_hotkey(_id: u16, _m: u32, _vk: u32) -> PyResult<bool> { Ok(true) }
#[pyfunction] pub fn unregister_hotkey(_id: u16) -> PyResult<bool> { Ok(true) }
#[pyfunction] pub fn get_current_thread_id() -> PyResult<u32> { Ok(0) }
#[pyfunction] pub fn post_thread_message(_id: u32, _m: u32, _w: usize, _l: isize) -> PyResult<bool> { Ok(true) }
#[pyfunction] pub fn get_message() -> PyResult<bool> { Ok(true) }
#[pyfunction] pub fn init_message_queue() -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn translate_dispatch() -> PyResult<()> { Ok(()) }

// Tray Stubs
#[pyfunction] pub fn tray_create_window(_class: String, _title: String) -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_get_message_ex(_py: Python<'_>) -> PyResult<Option<(usize, u32, usize, isize, i32)>> { Ok(None) }
#[pyfunction] pub fn tray_translate_dispatch(_h: usize, _m: u32, _w: usize, _l: isize) -> PyResult<()> { Ok(()) }

#[pyfunction]
pub fn tray_add_icon(
    hwnd_val: usize,
    hicon_val: usize,
    id: u32,
    tip: String,
    callback_msg: u32,
) -> PyResult<bool> {
    Ok(true)
}

#[pyfunction] pub fn tray_remove_icon(hwnd_val: usize, id: u32) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_destroy_window(hwnd_val: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_post_message(hwnd_val: usize, msg: u32, wparam: usize, lparam: isize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_load_icon(path: String, w: i32, h: i32) -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_load_default_icon() -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_destroy_icon(h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_create_popup_menu() -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_append_menu_item(hmenu_val: usize, flags: u32, id: u32, label: String) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_append_separator(hmenu_val: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_track_popup_menu(_py: Python<'_>, hmenu_val: usize, flags: u32, x: i32, y: i32, hwnd_val: usize) -> PyResult<u32> { Ok(0) }
#[pyfunction] pub fn tray_get_cursor_pos() -> PyResult<(i32, i32)> { Ok((0, 0)) }

#[pyfunction]
#[pyo3(signature = (tooltip, items, icon_path=None))]
pub fn tray_v2_create(
    tooltip: String,
    items: Vec<(String, String, bool)>,
    icon_path: Option<String>,
) -> PyResult<()> {
    Ok(())
}

#[pyfunction] pub fn tray_v2_poll_event(_py: Python<'_>) -> PyResult<Option<(String, String)>> { Ok(None) }
#[pyfunction] pub fn tray_v2_interrupt() -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_v2_destroy() -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn set_console_utf8() -> PyResult<()> { Ok(()) }
