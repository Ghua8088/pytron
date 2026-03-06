use pyo3::prelude::*;
use std::os::raw::{c_char, c_int, c_void};
use std::ffi::{CStr, CString};

extern "C" {
    fn gtk_init_check(argc: *mut c_int, argv: *mut *mut *mut c_char) -> c_int;
    // GtkMessageDialog
    fn gtk_message_dialog_new(
        parent: *mut c_void, flags: c_int, msg_type: c_int,
        buttons: c_int, format: *const c_char,
    ) -> *mut c_void;
    fn gtk_window_set_title(window: *mut c_void, title: *const c_char);
    fn gtk_dialog_run(dialog: *mut c_void) -> c_int;
    fn gtk_widget_destroy(widget: *mut c_void);
    // GtkFileChooserDialog
    fn gtk_file_chooser_dialog_new(
        title: *const c_char, parent: *mut c_void,
        action: c_int, first_button: *const c_char, // varargs follow
    ) -> *mut c_void;
    fn gtk_file_chooser_get_filename(chooser: *mut c_void) -> *mut c_char;
    fn g_free(ptr: *mut c_void);
}

fn ensure_gtk_init() {
    static INIT: std::sync::Once = std::sync::Once::new();
    INIT.call_once(|| unsafe {
        gtk_init_check(std::ptr::null_mut(), std::ptr::null_mut());
    });
}

// GTK constants
const GTK_DIALOG_MODAL: c_int  = 1;
const GTK_MESSAGE_INFO: c_int  = 0;
const GTK_MESSAGE_WARNING: c_int = 1;
const GTK_MESSAGE_ERROR: c_int = 3;
const GTK_BUTTONS_OK: c_int    = 1;
const GTK_RESPONSE_OK: c_int   = -5;

// GtkFileChooserAction
const GTK_FILE_CHOOSER_ACTION_OPEN: c_int = 0;
const GTK_FILE_CHOOSER_ACTION_SELECT_FOLDER: c_int = 2;
const GTK_FILE_CHOOSER_ACTION_SAVE: c_int = 1;

#[pyfunction]
pub fn message_box(py: Python<'_>, _hwnd_val: usize, title: String, message: String, level: String) -> PyResult<i32> {
    ensure_gtk_init();
    let c_title = CString::new(title.as_bytes()).unwrap();
    let c_msg   = CString::new(message.as_bytes()).unwrap();
    let msg_type = match level.as_str() {
        "error"   => GTK_MESSAGE_ERROR,
        "warning" => GTK_MESSAGE_WARNING,
        _         => GTK_MESSAGE_INFO,
    };
    let result = py.allow_threads(|| unsafe {
        let dlg = gtk_message_dialog_new(std::ptr::null_mut(), GTK_DIALOG_MODAL, msg_type, GTK_BUTTONS_OK, c_msg.as_ptr());
        gtk_window_set_title(dlg, c_title.as_ptr());
        let r = gtk_dialog_run(dlg);
        gtk_widget_destroy(dlg);
        r
    });
    Ok(result)
}

unsafe fn run_file_chooser(title: &str, action: c_int) -> Option<String> {
    let c_title  = CString::new(title.as_bytes()).unwrap();
    let c_ok     = CString::new("_OK").unwrap();
    let c_cancel = CString::new("_Cancel").unwrap();
    // gtk_file_chooser_dialog_new(title, parent, action, btn_label, btn_resp, NULL)
    // Use a simpler approach: create via gtk_dialog_new_with_buttons trick
    // Instead, simplest portable: just spawn zenity
    drop((c_title, c_ok, c_cancel));
    None // handled by zenity fallback below
}

fn zenity_file(title: &str, action: &str, save_name: Option<&str>) -> Option<String> {
    let mut cmd = std::process::Command::new("zenity");
    cmd.arg("--file-selection");
    cmd.arg("--title").arg(title);
    match action {
        "folder" => { cmd.arg("--directory"); }
        "save"   => {
            cmd.arg("--save");
            if let Some(name) = save_name {
                cmd.arg("--filename").arg(name);
            }
        }
        _ => {}
    }
    let out = cmd.output().ok()?;
    if out.status.success() {
        let path = String::from_utf8_lossy(&out.stdout).trim().to_owned();
        if !path.is_empty() { Some(path) } else { None }
    } else {
        None
    }
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, _default_path=None, _file_types=None))]
pub fn open_file_dialog(py: Python<'_>, hwnd_val: usize, title: String, _default_path: Option<String>, _file_types: Option<String>) -> PyResult<Option<String>> {
    let _ = hwnd_val;
    Ok(py.allow_threads(|| zenity_file(&title, "open", None)))
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, _default_path=None))]
pub fn open_folder_dialog(py: Python<'_>, hwnd_val: usize, title: String, _default_path: Option<String>) -> PyResult<Option<String>> {
    let _ = hwnd_val;
    Ok(py.allow_threads(|| zenity_file(&title, "folder", None)))
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, _default_path=None, _default_name=None, _file_types=None))]
pub fn save_file_dialog(py: Python<'_>, hwnd_val: usize, title: String, _default_path: Option<String>, _default_name: Option<String>, _file_types: Option<String>) -> PyResult<Option<String>> {
    let _ = hwnd_val;
    Ok(py.allow_threads(|| zenity_file(&title, "save", _default_name.as_deref())))
}
