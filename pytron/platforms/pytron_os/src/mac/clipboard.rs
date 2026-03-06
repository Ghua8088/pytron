use pyo3::prelude::*;
use objc::{class, msg_send, sel, sel_impl};
use cocoa::base::{id, nil};
use std::ffi::CStr;

unsafe fn nsstring(s: &str) -> id {
    let bytes = s.as_bytes();
    let ns: id = msg_send![class!(NSString), alloc];
    msg_send![ns, initWithBytes:bytes.as_ptr() length:bytes.len() encoding:4u64]
}

const PBOARD_TYPE: &str = "public.utf8-plain-text";

#[pyfunction]
pub fn set_clipboard_text(text: String) -> PyResult<bool> {
    unsafe {
        let pb: id   = msg_send![class!(NSPasteboard), generalPasteboard];
        let _: i64   = msg_send![pb, clearContents];
        let text_ns  = nsstring(&text);
        let arr: id  = msg_send![class!(NSArray), arrayWithObject: text_ns];
        let ok: i8   = msg_send![pb, writeObjects: arr];
        Ok(ok != 0)
    }
}

#[pyfunction]
pub fn get_clipboard_text() -> PyResult<Option<String>> {
    unsafe {
        let pb: id      = msg_send![class!(NSPasteboard), generalPasteboard];
        let type_ns     = nsstring(PBOARD_TYPE);
        let text_id: id = msg_send![pb, stringForType: type_ns];
        if text_id.is_null() {
            return Ok(None);
        }
        let c_str: *const i8 = msg_send![text_id, UTF8String];
        if c_str.is_null() { return Ok(None); }
        Ok(Some(CStr::from_ptr(c_str).to_string_lossy().into_owned()))
    }
}
