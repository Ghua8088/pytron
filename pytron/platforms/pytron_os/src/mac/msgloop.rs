/// macOS equivalents of the Windows message-queue helpers.
///
/// The Win32 message pump (GetMessage / PostThreadMessage) does not exist on
/// macOS.  The functions below provide compatible stubs so Python callers
/// written against the Windows API work without platform-gating:
///   - get_current_thread_id  → returns the Mach thread port (u32)
///   - post_thread_message    → posts to the platform tray queue
///   - get_message            → not used on macOS (tray uses tray_get_message_ex)
///   - init_message_queue     → no-op
///   - translate_dispatch     → no-op
use pyo3::prelude::*;
use crate::mac::tray::TRAY_MSG_QUEUE;

extern "C" {
    fn mach_thread_self() -> u32;
}

#[pyfunction]
pub fn get_current_thread_id() -> PyResult<u32> {
    Ok(unsafe { mach_thread_self() })
}

/// Push a message into the platform tray queue (used by Python `stop()` to
/// post WM_QUIT = 0x0012).
#[pyfunction]
pub fn post_thread_message(_thread_id: u32, msg: u32, wparam: usize, lparam: isize) -> PyResult<bool> {
    if let Ok(mut q) = TRAY_MSG_QUEUE.deque.lock() {
        q.push_back((0, msg, wparam, lparam));
        TRAY_MSG_QUEUE.cv.notify_one();
    }
    Ok(true)
}

/// Not used on macOS — the tray loop is driven by tray_get_message_ex.
#[pyfunction]
pub fn get_message(_py: Python<'_>) -> PyResult<Option<(u32, usize, isize)>> {
    Ok(None)
}

/// No-op: macOS has no Win32-style per-thread message queue to prime.
#[pyfunction]
pub fn init_message_queue() -> PyResult<()> {
    Ok(())
}

/// No-op: dispatch is automatic via NSRunLoop.
#[pyfunction]
pub fn translate_dispatch(_hwnd_val: usize, _msg: u32, _wparam: usize, _lparam: isize) -> PyResult<()> {
    Ok(())
}
