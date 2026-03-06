use pyo3::prelude::*;
use windows::Win32::Foundation::{HWND, WPARAM, LPARAM};
use windows::Win32::UI::WindowsAndMessaging::{
    GetMessageW, TranslateMessage, DispatchMessageW, PostThreadMessageW, PeekMessageW,
    MSG, PM_NOREMOVE,
};
use windows::Win32::System::Threading::GetCurrentThreadId;

#[pyfunction]
pub fn get_current_thread_id() -> PyResult<u32> {
    unsafe { Ok(GetCurrentThreadId()) }
}

#[pyfunction]
pub fn post_thread_message(thread_id: u32, msg: u32, wparam: usize, lparam: isize) -> PyResult<bool> {
    unsafe { Ok(PostThreadMessageW(thread_id, msg, WPARAM(wparam), LPARAM(lparam)).is_ok()) }
}

#[pyfunction]
pub fn get_message(py: Python<'_>) -> PyResult<Option<(u32, usize, isize)>> {
    let (res, message, wparam, lparam) = py.allow_threads(|| unsafe {
        let mut msg = MSG::default();
        let res = GetMessageW(&mut msg, HWND::default(), 0, 0);
        (res.0, msg.message, msg.wParam.0, msg.lParam.0)
    });
    if res > 0 { Ok(Some((message, wparam, lparam))) } else { Ok(None) }
}

/// Force-create a message queue for the current thread (needed before PostThreadMessageW).
#[pyfunction]
pub fn init_message_queue() -> PyResult<()> {
    unsafe {
        let mut msg = MSG::default();
        PeekMessageW(&mut msg, HWND::default(), 0, 0, PM_NOREMOVE);
    }
    Ok(())
}

/// TranslateMessage + DispatchMessageW. hwnd_val == 0 is valid for thread messages.
#[pyfunction]
pub fn translate_dispatch(hwnd_val: usize, msg: u32, wparam: usize, lparam: isize) -> PyResult<()> {
    unsafe {
        let m = MSG { hwnd: HWND(hwnd_val as isize), message: msg, wParam: WPARAM(wparam), lParam: LPARAM(lparam), ..Default::default() };
        let _ = TranslateMessage(&m);
        DispatchMessageW(&m);
    }
    Ok(())
}
