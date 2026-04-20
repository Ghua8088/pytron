use pyo3::prelude::*;
use rfd::FileDialog;
use arboard::Clipboard;
use notify_rust::Notification;

#[pyfunction]
pub fn message_box(_hwnd_val: usize, title: String, message: String, _style: u32) -> PyResult<u32> {
    // RFD doesn't have a dedicated message_box yet in 0.14 standardly for "OK" only, 
    // but we can use a basic confirmation or just log for now if we want to be exact.
    // However, RFD is great for Yes/No. 
    println!("[Linux] Message Box: {} - {}", title, message);
    Ok(1) // IDOK
}

#[pyfunction]
#[pyo3(signature = (_hwnd_val, title, _default_path=None, _file_types=None))]
pub fn open_file_dialog(_hwnd_val: usize, title: String, _default_path: Option<String>, _file_types: Option<String>) -> PyResult<Option<String>> {
    let file = FileDialog::new()
        .set_title(&title)
        .pick_file();
    
    Ok(file.map(|p| p.to_string_lossy().to_string()))
}

#[pyfunction]
#[pyo3(signature = (_hwnd_val, title, _default_path=None, _default_name=None, _file_types=None))]
pub fn save_file_dialog(_hwnd_val: usize, title: String, _default_path: Option<String>, _default_name: Option<String>, _file_types: Option<String>) -> PyResult<Option<String>> {
    let file = FileDialog::new()
        .set_title(&title)
        .save_file();
        
    Ok(file.map(|p| p.to_string_lossy().to_string()))
}

#[pyfunction]
#[pyo3(signature = (_hwnd_val, title, _default_path=None))]
pub fn open_folder_dialog(_hwnd_val: usize, title: String, _default_path: Option<String>) -> PyResult<Option<String>> {
    let folder = FileDialog::new()
        .set_title(&title)
        .pick_folder();
        
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
#[pyo3(signature = (_hwnd_val, title, message, _icon_path=None))]
pub fn show_notification(_hwnd_val: usize, title: String, message: String, _icon_path: Option<String>) -> PyResult<()> {
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
#[pyo3(signature = (_h, _x, _y, _w, _h2, _no_move=None, _no_size=None))]
pub fn set_bounds(_h: usize, _x: i32, _y: i32, _w: i32, _h2: i32, _no_move: Option<bool>, _no_size: Option<bool>) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn toggle_maximize(_h: usize) -> PyResult<bool> { Ok(false) }
#[pyfunction] pub fn set_always_on_top(_h: usize, _e: bool) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn start_drag(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn is_visible(_h: usize) -> PyResult<bool> { Ok(true) }
#[pyfunction]
#[pyo3(signature = (_h, _width=None, _height=None))]
pub fn center(_h: usize, _width: Option<i32>, _height: Option<i32>) -> PyResult<()> { Ok(()) }
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
#[pyfunction] pub fn tray_create_window() -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_get_message_ex() -> PyResult<bool> { Ok(false) }
#[pyfunction] pub fn tray_translate_dispatch() -> PyResult<()> { Ok(()) }
#[pyfunction] #[pyo3(signature = (_h, _t, _i=None))] pub fn tray_add_icon(_h: usize, _t: String, _i: Option<String>) -> PyResult<bool> { Ok(true) }
#[pyfunction] pub fn tray_remove_icon(_h: usize) -> PyResult<bool> { Ok(true) }
#[pyfunction] pub fn tray_destroy_window(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_post_message(_h: usize, _m: u32) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_load_icon(_p: String) -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_load_default_icon() -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_destroy_icon(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_create_popup_menu() -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_append_menu_item(_h: usize, _id: usize, _t: String) -> PyResult<bool> { Ok(true) }
#[pyfunction] pub fn tray_append_separator(_h: usize) -> PyResult<bool> { Ok(true) }
#[pyfunction] pub fn tray_track_popup_menu(_wh: usize, _mh: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_get_cursor_pos() -> PyResult<(i32, i32)> { Ok((0,0)) }
#[pyfunction] #[pyo3(signature = (_t, _i=None))] pub fn tray_v2_create(_t: String, _i: Option<String>) -> PyResult<usize> { Ok(0) }
#[pyfunction] pub fn tray_v2_poll_event(_h: usize) -> PyResult<Option<String>> { Ok(None) }
#[pyfunction] pub fn tray_v2_interrupt(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn tray_v2_destroy(_h: usize) -> PyResult<()> { Ok(()) }
#[pyfunction] pub fn set_console_utf8() -> PyResult<()> { Ok(()) }
