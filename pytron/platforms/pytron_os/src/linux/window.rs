use pyo3::prelude::*;
use std::os::raw::{c_char, c_int, c_void, c_double};
use std::ffi::CString;

// ─── GTK/GDK extern C ────────────────────────────────────────────────────────

extern "C" {
    fn gtk_window_set_skip_taskbar_hint(window: *mut c_void, setting: c_int);
    fn gtk_window_set_decorated(window: *mut c_void, setting: c_int);
    fn gtk_widget_hide(widget: *mut c_void);
    fn gtk_widget_show(widget: *mut c_void);
    fn gtk_widget_get_visible(widget: *mut c_void) -> c_int;
    fn gtk_window_iconify(window: *mut c_void);
    fn gtk_window_deiconify(window: *mut c_void);
    fn gtk_window_maximize(window: *mut c_void);
    fn gtk_window_unmaximize(window: *mut c_void);
    fn gtk_window_is_maximized(window: *mut c_void) -> c_int;
    fn gtk_window_close(window: *mut c_void);
    fn gtk_window_move(window: *mut c_void, x: c_int, y: c_int);
    fn gtk_window_resize(window: *mut c_void, width: c_int, height: c_int);
    fn gtk_window_get_size(window: *mut c_void, width: *mut c_int, height: *mut c_int);
    fn gtk_window_set_keep_above(window: *mut c_void, setting: c_int);
    fn gtk_window_fullscreen(window: *mut c_void);
    fn gtk_window_unfullscreen(window: *mut c_void);
    fn gtk_window_present(window: *mut c_void);
    fn gtk_window_set_icon_from_file(window: *mut c_void, filename: *const c_char, err: *mut *mut c_void) -> c_int;
    fn gdk_screen_get_default() -> *mut c_void;
    fn gdk_screen_get_width(screen: *mut c_void) -> c_int;
    fn gdk_screen_get_height(screen: *mut c_void) -> c_int;
    fn gtk_init_check(argc: *mut c_int, argv: *mut *mut *mut c_char) -> c_int;
}

fn ensure_gtk_init() {
    static INIT: std::sync::Once = std::sync::Once::new();
    INIT.call_once(|| unsafe {
        gtk_init_check(std::ptr::null_mut(), std::ptr::null_mut());
    });
}

// ─── Public API ──────────────────────────────────────────────────────────────

#[pyfunction]
pub fn set_utility_window(hwnd_val: usize, enable: bool) -> PyResult<()> {
    ensure_gtk_init();
    let win = hwnd_val as *mut c_void;
    unsafe { gtk_window_set_skip_taskbar_hint(win, if enable { 1 } else { 0 }); }
    Ok(())
}

#[pyfunction]
pub fn make_frameless(hwnd_val: usize) -> PyResult<()> {
    ensure_gtk_init();
    let win = hwnd_val as *mut c_void;
    unsafe { gtk_window_set_decorated(win, 0); }
    Ok(())
}

#[pyfunction]
pub fn minimize(hwnd_val: usize) -> PyResult<()> {
    ensure_gtk_init();
    unsafe { gtk_window_iconify(hwnd_val as *mut c_void); }
    Ok(())
}

#[pyfunction]
pub fn set_bounds(hwnd_val: usize, x: i32, y: i32, width: i32, height: i32) -> PyResult<()> {
    ensure_gtk_init();
    let win = hwnd_val as *mut c_void;
    unsafe {
        gtk_window_move(win, x, y);
        gtk_window_resize(win, width, height);
    }
    Ok(())
}

#[pyfunction]
pub fn close(hwnd_val: usize) -> PyResult<()> {
    ensure_gtk_init();
    unsafe { gtk_window_close(hwnd_val as *mut c_void); }
    Ok(())
}

#[pyfunction]
pub fn toggle_maximize(hwnd_val: usize) -> PyResult<bool> {
    ensure_gtk_init();
    let win = hwnd_val as *mut c_void;
    unsafe {
        if gtk_window_is_maximized(win) != 0 {
            gtk_window_unmaximize(win);
            Ok(false)
        } else {
            gtk_window_maximize(win);
            Ok(true)
        }
    }
}

#[pyfunction]
pub fn set_always_on_top(hwnd_val: usize, enable: bool) -> PyResult<()> {
    ensure_gtk_init();
    unsafe { gtk_window_set_keep_above(hwnd_val as *mut c_void, if enable { 1 } else { 0 }); }
    Ok(())
}

#[pyfunction]
pub fn start_drag(_hwnd_val: usize) -> PyResult<()> {
    // Requires current GdkEvent — not available here; no-op with note
    Ok(())
}

#[pyfunction]
pub fn hide(hwnd_val: usize) -> PyResult<()> {
    ensure_gtk_init();
    unsafe { gtk_widget_hide(hwnd_val as *mut c_void); }
    Ok(())
}

#[pyfunction]
pub fn is_visible(hwnd_val: usize) -> PyResult<bool> {
    ensure_gtk_init();
    Ok(unsafe { gtk_widget_get_visible(hwnd_val as *mut c_void) } != 0)
}

#[pyfunction]
pub fn show(hwnd_val: usize) -> PyResult<()> {
    ensure_gtk_init();
    unsafe {
        gtk_widget_show(hwnd_val as *mut c_void);
        gtk_window_present(hwnd_val as *mut c_void);
    }
    Ok(())
}

#[pyfunction]
pub fn center(hwnd_val: usize) -> PyResult<()> {
    ensure_gtk_init();
    let win = hwnd_val as *mut c_void;
    unsafe {
        let screen = gdk_screen_get_default();
        let sw = gdk_screen_get_width(screen);
        let sh = gdk_screen_get_height(screen);
        let mut ww = 0i32;
        let mut wh = 0i32;
        gtk_window_get_size(win, &mut ww, &mut wh);
        gtk_window_move(win, (sw - ww) / 2, (sh - wh) / 2);
    }
    Ok(())
}

#[pyfunction]
pub fn set_border_color(_hwnd_val: usize, _color_ref: u32) -> PyResult<()> {
    Ok(()) // Not directly supported without CSS provider
}

#[pyfunction]
pub fn set_window_icon(hwnd_val: usize, icon_path: String) -> PyResult<()> {
    ensure_gtk_init();
    let path = CString::new(icon_path).unwrap();
    unsafe {
        gtk_window_set_icon_from_file(hwnd_val as *mut c_void, path.as_ptr(), std::ptr::null_mut());
    }
    Ok(())
}

#[pyfunction]
pub fn set_fullscreen(hwnd_val: usize, enable: bool) -> PyResult<()> {
    ensure_gtk_init();
    let win = hwnd_val as *mut c_void;
    unsafe {
        if enable { gtk_window_fullscreen(win); } else { gtk_window_unfullscreen(win); }
    }
    Ok(())
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, message, icon_path=None))]
pub fn show_notification(_hwnd_val: usize, title: String, message: String, _icon_path: Option<String>) -> PyResult<()> {
    // Use notify-send (libnotify CLI, present on most desktops)
    std::process::Command::new("notify-send")
        .arg("--")
        .arg(&title)
        .arg(&message)
        .spawn()
        .ok();
    Ok(())
}

#[pyfunction]
pub fn set_taskbar_progress(_hwnd_val: usize, _state: String, _value: u64, _max_value: u64) -> PyResult<()> {
    // Unity launcher API needed; stub
    Ok(())
}

#[pyfunction]
pub fn set_app_id(_app_id: String) -> PyResult<()> {
    Ok(())
}

#[pyfunction]
pub fn set_launch_on_boot(app_name: String, exe_path: String, enable: bool) -> PyResult<bool> {
    use std::{fs, path::PathBuf};
    let home = std::env::var("HOME").map(PathBuf::from)
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("No HOME"))?;
    let dir  = home.join(".config/autostart");
    let file = dir.join(format!("{}.desktop", app_name));
    if enable {
        let _ = fs::create_dir_all(&dir);
        let content = format!(
            "[Desktop Entry]\nType=Application\nName={}\nExec={}\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\n",
            app_name, exe_path
        );
        fs::write(file, content)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    } else if file.exists() {
        let _ = fs::remove_file(file);
    }
    Ok(true)
}
