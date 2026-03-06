use pyo3::prelude::*;
use objc::{class, msg_send, sel, sel_impl};
use cocoa::base::{id, nil};
use std::ffi::CStr;

unsafe fn nsstring(s: &str) -> id {
    let bytes = s.as_bytes();
    let ns: id = msg_send![class!(NSString), alloc];
    msg_send![ns, initWithBytes:bytes.as_ptr() length:bytes.len() encoding:4u64]
}

unsafe fn nsstring_to_string(ns: id) -> Option<String> {
    if ns.is_null() { return None; }
    let c_str: *const i8 = msg_send![ns, UTF8String];
    if c_str.is_null() { return None; }
    Some(CStr::from_ptr(c_str).to_string_lossy().into_owned())
}

#[pyfunction]
pub fn message_box(py: Python<'_>, _hwnd_val: usize, title: String, message: String, level: String) -> PyResult<i32> {
    let result = py.allow_threads(|| unsafe {
        let alert: id  = msg_send![class!(NSAlert), new];
        let title_ns   = nsstring(&title);
        let msg_ns     = nsstring(&message);
        let _: ()      = msg_send![alert, setMessageText: title_ns];
        let _: ()      = msg_send![alert, setInformativeText: msg_ns];
        // NSAlertStyle: 0=informational, 1=warning, 2=critical
        let style: usize = match level.as_str() {
            "error"   => 2,
            "warning" => 1,
            _         => 0,
        };
        let _: () = msg_send![alert, setAlertStyle: style];
        let res: i64 = msg_send![alert, runModal]; // NSAlertFirstButtonReturn = 1000
        res as i32
    });
    Ok(result)
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, _default_path=None, _file_types=None))]
pub fn open_file_dialog(py: Python<'_>, hwnd_val: usize, title: String, _default_path: Option<String>, _file_types: Option<String>) -> PyResult<Option<String>> {
    let _ = hwnd_val;
    py.allow_threads(|| unsafe {
        let panel: id  = msg_send![class!(NSOpenPanel), openPanel];
        let title_ns   = nsstring(&title);
        let _: ()      = msg_send![panel, setTitle: title_ns];
        let _: ()      = msg_send![panel, setCanChooseFiles: 1_i8];
        let _: ()      = msg_send![panel, setCanChooseDirectories: 0_i8];
        let result: i64 = msg_send![panel, runModal]; // NSModalResponseOK = 1
        if result == 1 {
            let url: id  = msg_send![panel, URL];
            let path: id = msg_send![url, path];
            Ok(nsstring_to_string(path))
        } else {
            Ok(None)
        }
    })
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, _default_path=None))]
pub fn open_folder_dialog(py: Python<'_>, hwnd_val: usize, title: String, _default_path: Option<String>) -> PyResult<Option<String>> {
    let _ = hwnd_val;
    py.allow_threads(|| unsafe {
        let panel: id  = msg_send![class!(NSOpenPanel), openPanel];
        let title_ns   = nsstring(&title);
        let _: ()      = msg_send![panel, setTitle: title_ns];
        let _: ()      = msg_send![panel, setCanChooseFiles: 0_i8];
        let _: ()      = msg_send![panel, setCanChooseDirectories: 1_i8];
        let result: i64 = msg_send![panel, runModal];
        if result == 1 {
            let url: id  = msg_send![panel, URL];
            let path: id = msg_send![url, path];
            Ok(nsstring_to_string(path))
        } else {
            Ok(None)
        }
    })
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, _default_path=None, _default_name=None, _file_types=None))]
pub fn save_file_dialog(py: Python<'_>, hwnd_val: usize, title: String, _default_path: Option<String>, _default_name: Option<String>, _file_types: Option<String>) -> PyResult<Option<String>> {
    let _ = hwnd_val;
    py.allow_threads(|| unsafe {
        let panel: id  = msg_send![class!(NSSavePanel), savePanel];
        let title_ns   = nsstring(&title);
        let _: ()      = msg_send![panel, setTitle: title_ns];
        let result: i64 = msg_send![panel, runModal];
        if result == 1 {
            let url: id  = msg_send![panel, URL];
            let path: id = msg_send![url, path];
            Ok(nsstring_to_string(path))
        } else {
            Ok(None)
        }
    })
}
