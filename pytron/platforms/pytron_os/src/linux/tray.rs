/// Linux system tray via GtkStatusIcon.
///
/// Uses the same Mutex<VecDeque> pattern as the macOS implementation so that
/// Python's tray.py event loop works identically on all platforms.
use pyo3::prelude::*;
use once_cell::sync::Lazy;
use dashmap::DashMap;
use std::sync::{Mutex, Condvar};
use std::collections::VecDeque;
use std::os::raw::{c_char, c_int, c_uint, c_void};
use std::ffi::CString;

// ─── GTK FFI ─────────────────────────────────────────────────────────────────

extern "C" {
    fn gtk_init_check(argc: *mut c_int, argv: *mut *mut *mut c_char) -> c_int;
    fn gtk_events_pending() -> c_int;
    fn gtk_main_iteration_do(blocking: c_int) -> c_int;
    fn gtk_status_icon_new() -> *mut c_void;
    fn gtk_status_icon_set_from_file(icon: *mut c_void, filename: *const c_char);
    fn gtk_status_icon_set_tooltip_text(icon: *mut c_void, tooltip: *const c_char);
    fn gtk_status_icon_set_visible(icon: *mut c_void, visible: c_int);
    fn g_object_unref(obj: *mut c_void);
    // GtkMenu
    fn gtk_menu_new() -> *mut c_void;
    fn gtk_menu_item_new_with_label(label: *const c_char) -> *mut c_void;
    fn gtk_separator_menu_item_new() -> *mut c_void;
    fn gtk_menu_shell_append(shell: *mut c_void, child: *mut c_void);
    fn gtk_widget_show_all(widget: *mut c_void);
    fn gtk_menu_popup_at_pointer(menu: *mut c_void, trigger_event: *mut c_void);
    // GLib signals
    fn g_signal_connect_data(
        instance: *mut c_void,
        detailed_signal: *const c_char,
        c_handler: *const c_void,
        data: *mut c_void,
        destroy_data: *mut c_void,
        connect_flags: c_uint,
    ) -> u64;
}

// ─── Platform message queue ───────────────────────────────────────────────────

pub struct MsgQ {
    pub deque: Mutex<VecDeque<(usize, u32, usize, isize)>>,
    pub cv:    Condvar,
}

pub static TRAY_MSG_QUEUE: Lazy<MsgQ> = Lazy::new(|| MsgQ {
    deque: Mutex::new(VecDeque::new()),
    cv:    Condvar::new(),
});

fn push_msg(hwnd: usize, msg: u32, wp: usize, lp: isize) {
    if let Ok(mut q) = TRAY_MSG_QUEUE.deque.lock() {
        q.push_back((hwnd, msg, wp, lp));
        TRAY_MSG_QUEUE.cv.notify_one();
    }
}

// ─── Stored tray state ────────────────────────────────────────────────────────

struct TrayState {
    gtk_icon: usize, // GtkStatusIcon*
}

static TRAY_STATE: Lazy<DashMap<usize, TrayState>> = Lazy::new(DashMap::new);

fn ensure_gtk_init() {
    static INIT: std::sync::Once = std::sync::Once::new();
    INIT.call_once(|| unsafe {
        gtk_init_check(std::ptr::null_mut(), std::ptr::null_mut());
    });
}

// ─── GLib signal callback ────────────────────────────────────────────────────

// Called when the status icon is activated (left-click)
unsafe extern "C" fn on_activate(icon: *mut c_void, data: *mut c_void) {
    let hwnd_val = data as usize;
    push_msg(hwnd_val, 0x0201, 0, 0); // WM_LBUTTONDOWN-style
}

// Called for right-click popup-menu request
unsafe extern "C" fn on_popup_menu(icon: *mut c_void, button: c_uint, time: u32, data: *mut c_void) {
    let hwnd_val = data as usize;
    push_msg(hwnd_val, 0x0205, 0, 0); // WM_RBUTTONUP-style
}

const WM_QUIT: u32 = 0x0012;

// ─── tray_create_window ───────────────────────────────────────────────────────

#[pyfunction]
pub fn tray_create_window(_class_name: String, _title: String) -> PyResult<usize> {
    Ok(1) // fake HWND; icon created in tray_add_icon
}

// ─── Event pump ───────────────────────────────────────────────────────────────

#[pyfunction]
pub fn tray_get_message_ex(py: Python<'_>) -> PyResult<Option<(usize, u32, usize, isize)>> {
    let result = py.allow_threads(|| {
        loop {
            let msg = {
                let mut q = TRAY_MSG_QUEUE.deque.lock().unwrap();
                q.pop_front()
            };
            if let Some(m) = msg { return m; }
            // Drain GTK events for 20 ms
            unsafe {
                if gtk_events_pending() != 0 {
                    gtk_main_iteration_do(0);
                } else {
                    std::thread::sleep(std::time::Duration::from_millis(20));
                }
            }
        }
    });
    if result.1 == WM_QUIT { Ok(None) } else { Ok(Some(result)) }
}

#[pyfunction]
pub fn tray_translate_dispatch(_hwnd_val: usize, _msg: u32, _wparam: usize, _lparam: isize) -> PyResult<()> {
    Ok(())
}

// ─── Icon lifecycle ───────────────────────────────────────────────────────────

#[pyfunction]
pub fn tray_add_icon(hwnd_val: usize, hicon_val: usize, _id: u32, tip: String, _callback_msg: u32) -> PyResult<bool> {
    ensure_gtk_init();
    let c_tip = CString::new(tip.as_bytes()).unwrap();
    unsafe {
        let icon = gtk_status_icon_new();
        if icon.is_null() { return Ok(false); }

        gtk_status_icon_set_tooltip_text(icon, c_tip.as_ptr());

        // Apply icon if caller provided a path (from tray_load_icon)
        if hicon_val != 0 {
            gtk_status_icon_set_from_file(icon, hicon_val as *const c_char);
        }

        gtk_status_icon_set_visible(icon, 1);

        // Connect signals
        let sig_activate = CString::new("activate").unwrap();
        let sig_popup    = CString::new("popup-menu").unwrap();
        g_signal_connect_data(icon, sig_activate.as_ptr(), on_activate as *const c_void, hwnd_val as *mut c_void, std::ptr::null_mut(), 0);
        g_signal_connect_data(icon, sig_popup.as_ptr(), on_popup_menu as *const c_void, hwnd_val as *mut c_void, std::ptr::null_mut(), 0);

        TRAY_STATE.insert(hwnd_val, TrayState { gtk_icon: icon as usize });
        Ok(true)
    }
}

#[pyfunction]
pub fn tray_remove_icon(hwnd_val: usize, _id: u32) -> PyResult<()> {
    if let Some((_, state)) = TRAY_STATE.remove(&hwnd_val) {
        unsafe {
            gtk_status_icon_set_visible(state.gtk_icon as *mut c_void, 0);
            g_object_unref(state.gtk_icon as *mut c_void);
        }
    }
    Ok(())
}

#[pyfunction]
pub fn tray_destroy_window(_hwnd_val: usize) -> PyResult<()> {
    Ok(())
}

#[pyfunction]
pub fn tray_post_message(hwnd_val: usize, msg: u32, wparam: usize, lparam: isize) -> PyResult<()> {
    push_msg(hwnd_val, msg, wparam, lparam);
    Ok(())
}

// ─── Icon loading ─────────────────────────────────────────────────────────────

/// Load icon from file — on Linux we just store the path as a usize hash.
/// The actual path is applied in tray_add_icon/update via gtk_status_icon_set_from_file.
#[pyfunction]
pub fn tray_load_icon(path: String, _w: i32, _h: i32) -> PyResult<usize> {
    let cstr  = CString::new(path).unwrap();
    let ptr   = cstr.into_raw();
    Ok(ptr as usize) // caller must call tray_destroy_icon to free
}

#[pyfunction]
pub fn tray_load_default_icon() -> PyResult<usize> {
    Ok(0) // 0 = no custom icon; tray_add_icon will use GTK default
}

#[pyfunction]
pub fn tray_destroy_icon(hicon_val: usize) -> PyResult<()> {
    if hicon_val != 0 {
        // Reclaim the CString we allocated in tray_load_icon
        unsafe { drop(CString::from_raw(hicon_val as *mut c_char)); }
    }
    Ok(())
}

// ─── Context menu ─────────────────────────────────────────────────────────────

#[pyfunction]
pub fn tray_create_popup_menu() -> PyResult<usize> {
    ensure_gtk_init();
    let menu = unsafe { gtk_menu_new() };
    Ok(menu as usize)
}

#[pyfunction]
pub fn tray_append_menu_item(hmenu_val: usize, _flags: u32, _id: u32, label: String) -> PyResult<()> {
    let c_label = CString::new(label.as_bytes()).unwrap();
    unsafe {
        let item = gtk_menu_item_new_with_label(c_label.as_ptr());
        gtk_menu_shell_append(hmenu_val as *mut c_void, item);
    }
    Ok(())
}

#[pyfunction]
pub fn tray_append_separator(hmenu_val: usize) -> PyResult<()> {
    unsafe {
        let sep = gtk_separator_menu_item_new();
        gtk_menu_shell_append(hmenu_val as *mut c_void, sep);
    }
    Ok(())
}

#[pyfunction]
pub fn tray_track_popup_menu(hmenu_val: usize, _flags: u32, _x: i32, _y: i32, _hwnd_val: usize) -> PyResult<()> {
    unsafe {
        let menu = hmenu_val as *mut c_void;
        gtk_widget_show_all(menu);
        gtk_menu_popup_at_pointer(menu, std::ptr::null_mut());
    }
    Ok(())
}

#[pyfunction]
pub fn tray_get_cursor_pos() -> PyResult<(i32, i32)> {
    // GDK device position; requires GdkDisplay/GdkDevice.
    // For simplicity return (0, 0) — menus pop at pointer anyway.
    Ok((0, 0))
}
