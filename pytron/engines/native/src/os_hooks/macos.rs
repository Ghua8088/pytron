use pyo3::prelude::*;
use pyo3::PyObject;
use rfd::FileDialog;
use arboard::Clipboard;
use notify_rust::Notification;

#[pyfunction]
pub fn message_box(
    _py: Python<'_>,
    _hwnd_val: usize,
    title: String,
    message: String,
    _level: String,
) -> PyResult<i32> {
    println!("[macOS] Message Box: {} - {}", title, message);
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
    let _ = hwnd_val;
    let mut dialog = FileDialog::new().set_title(&title);
    if let Some(path) = default_path {
        dialog = dialog.set_directory(path);
    }
    let folder = dialog.pick_file();
    Ok(folder.map(|p| p.to_string_lossy().to_string()))
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
    let _ = hwnd_val;
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
    let _ = hwnd_val;
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
pub fn show_notification(_hwnd_val: usize, title: String, message: String, _icon_path: Option<String>) -> PyResult<()> {
    let _ = Notification::new()
        .summary(&title)
        .body(&message)
        .show();
    Ok(())
}

// Stubs for Windows-only features
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
    _hwnd_val: usize,
    _x: i32,
    _y: i32,
    _width: i32,
    _height: i32,
    _no_move: Option<bool>,
    _no_size: Option<bool>,
) -> PyResult<()> {
    Ok(())
}

#[pyfunction] pub fn toggle_maximize(_h: usize) -> PyResult<bool> { Ok(false) }
#[pyfunction] pub fn set_always_on_top(_h: usize, _e: bool) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn start_drag(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn is_visible(_h: usize) -> PyResult<bool> { Ok(true) }

#[pyfunction]
#[pyo3(signature = (hwnd_val, width=None, height=None))]
pub fn center(_hwnd_val: usize, _width: Option<i32>, _height: Option<i32>) -> PyResult<()> {
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
    _hwnd_val: usize,
    _hicon_val: usize,
    _id: u32,
    _tip: String,
    _callback_msg: u32,
) -> PyResult<bool> {
    Ok(true)
}

#[pyfunction] pub fn tray_remove_icon(_hwnd_val: usize, _id: u32) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_destroy_window(_hwnd_val: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_post_message(_hwnd_val: usize, _msg: u32, _wparam: usize, _lparam: isize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_load_icon(_path: String, _w: i32, _h: i32) -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_load_default_icon() -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_destroy_icon(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_create_popup_menu() -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_append_menu_item(_hmenu_val: usize, _flags: u32, _id: u32, _label: String) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_append_separator(_hmenu_val: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_track_popup_menu(_py: Python<'_>, _hmenu_val: usize, _flags: u32, _x: i32, _y: i32, _hwnd_val: usize) -> PyResult<u32> { Ok(0) }
#[pyfunction] pub fn tray_get_cursor_pos() -> PyResult<(i32, i32)> { Ok((0, 0)) }

#[pyfunction]
#[pyo3(signature = (tooltip, items, icon_path=None))]
pub fn tray_v2_create(
    _tooltip: String,
    _items: Vec<(String, String, bool)>,
    _icon_path: Option<String>,
) -> PyResult<()> {
    Ok(())
}

#[pyfunction] pub fn tray_v2_poll_event(_py: Python<'_>) -> PyResult<Option<(String, String)>> { Ok(None) }
#[pyfunction] pub fn tray_v2_interrupt() -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_v2_destroy() -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn set_console_utf8() -> PyResult<()> { Ok(()) }
