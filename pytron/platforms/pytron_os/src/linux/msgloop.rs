/// Linux message-queue stubs — POSIX thread ID + tray-queue forwarding.
use pyo3::prelude::*;
use crate::linux::tray::TRAY_MSG_QUEUE;

extern "C" {
    fn pthread_self() -> u64;
}

#[pyfunction]
pub fn get_current_thread_id() -> PyResult<u32> {
    Ok(unsafe { pthread_self() } as u32)
}

/// Forwards a message to the platform tray queue (used by Python stop() to
/// send WM_QUIT = 0x0012).
#[pyfunction]
pub fn post_thread_message(_thread_id: u32, msg: u32, wparam: usize, lparam: isize) -> PyResult<bool> {
    if let Ok(mut q) = TRAY_MSG_QUEUE.deque.lock() {
        q.push_back((0, msg, wparam, lparam));
        TRAY_MSG_QUEUE.cv.notify_one();
    }
    Ok(true)
}

/// Not used on Linux — the tray loop is driven by tray_get_message_ex.
#[pyfunction]
pub fn get_message(_py: Python<'_>) -> PyResult<Option<(u32, usize, isize)>> {
    Ok(None)
}

/// No-op: Linux GLib loop handles message queuing internally.
#[pyfunction]
pub fn init_message_queue() -> PyResult<()> {
    Ok(())
}

/// No-op: dispatch is handled by GLib/GTK event loop.
#[pyfunction]
pub fn translate_dispatch(_hwnd_val: usize, _msg: u32, _wparam: usize, _lparam: isize) -> PyResult<()> {
    Ok(())
}
