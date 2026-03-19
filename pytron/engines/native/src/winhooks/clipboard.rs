use pyo3::prelude::*;
use windows::Win32::Foundation::{HANDLE, HWND};
use windows::Win32::System::DataExchange::{
    CloseClipboard, EmptyClipboard, GetClipboardData, OpenClipboard, SetClipboardData,
};
use windows::Win32::System::Memory::{GHND, GlobalAlloc, GlobalLock, GlobalUnlock};

#[pyfunction]
pub fn set_clipboard_text(py: Python<'_>, text: String) -> PyResult<bool> {
    let text_u16: Vec<u16> = text.encode_utf16().chain(std::iter::once(0)).collect();
    let size = text_u16.len() * 2;
    py.allow_threads(|| unsafe {
        if OpenClipboard(HWND::default()).is_err() {
            return Ok(false);
        }
        let _ = EmptyClipboard();

        let h_mem = GlobalAlloc(GHND, size)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        let p_mem = GlobalLock(h_mem);
        if p_mem.is_null() {
            let _ = CloseClipboard();
            return Ok(false);
        }

        std::ptr::copy_nonoverlapping(text_u16.as_ptr(), p_mem as *mut u16, text_u16.len());
        let _ = GlobalUnlock(h_mem);

        let res = SetClipboardData(13, HANDLE(h_mem.0 as isize));
        let _ = CloseClipboard();
        Ok(res.is_ok())
    })
}

#[pyfunction]
pub fn get_clipboard_text(py: Python<'_>) -> PyResult<Option<String>> {
    py.allow_threads(|| unsafe {
        if OpenClipboard(HWND::default()).is_err() {
            return Ok(None);
        }

        let result = if let Ok(h_ptr) = GetClipboardData(13) {
            let h_mem = windows::Win32::Foundation::HGLOBAL(h_ptr.0 as *mut _);
            let p_mem = GlobalLock(h_mem);
            let text = if !p_mem.is_null() {
                let ptr = p_mem as *const u16;
                let mut len = 0;
                while *ptr.add(len) != 0 {
                    len += 1;
                }
                let s = String::from_utf16_lossy(std::slice::from_raw_parts(ptr, len));
                let _ = GlobalUnlock(h_mem);
                Some(s)
            } else {
                None
            };
            text
        } else {
            None
        };

        let _ = CloseClipboard();
        Ok(result)
    })
}
