use pyo3::prelude::*;
use std::os::raw::{c_char, c_int, c_void};
use std::ffi::{CStr, CString};

extern "C" {
    fn gdk_atom_intern(atom_name: *const c_char, only_if_exists: c_int) -> usize;
    fn gtk_clipboard_get(selection: usize) -> *mut c_void;
    fn gtk_clipboard_set_text(clipboard: *mut c_void, text: *const c_char, len: c_int);
    fn gtk_clipboard_wait_for_text(clipboard: *mut c_void) -> *mut c_char;
    fn g_free(ptr: *mut c_void);
    fn gtk_init_check(argc: *mut c_int, argv: *mut *mut *mut c_char) -> c_int;
}

fn ensure_gtk_init() {
    static INIT: std::sync::Once = std::sync::Once::new();
    INIT.call_once(|| unsafe {
        gtk_init_check(std::ptr::null_mut(), std::ptr::null_mut());
    });
}

fn clipboard() -> *mut c_void {
    let atom_name = CString::new("CLIPBOARD").unwrap();
    let atom = unsafe { gdk_atom_intern(atom_name.as_ptr(), 0) };
    unsafe { gtk_clipboard_get(atom) }
}

#[pyfunction]
pub fn set_clipboard_text(text: String) -> PyResult<bool> {
    ensure_gtk_init();
    let cstr = CString::new(text.as_bytes())
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    unsafe {
        let cb = clipboard();
        gtk_clipboard_set_text(cb, cstr.as_ptr(), text.len() as c_int);
    }
    Ok(true)
}

#[pyfunction]
pub fn get_clipboard_text() -> PyResult<Option<String>> {
    ensure_gtk_init();
    unsafe {
        let cb  = clipboard();
        let ptr = gtk_clipboard_wait_for_text(cb);
        if ptr.is_null() {
            return Ok(None);
        }
        let s = CStr::from_ptr(ptr).to_string_lossy().into_owned();
        g_free(ptr as *mut c_void);
        Ok(Some(s))
    }
}
