use pyo3::prelude::*;
use windows::Win32::System::Console::{SetConsoleCP, SetConsoleOutputCP};

/// Set Windows console input/output code page to UTF-8 (65001).
/// Returns true if both calls succeed.
#[pyfunction]
pub fn set_console_utf8() -> PyResult<bool> {
    unsafe { Ok(SetConsoleOutputCP(65001).is_ok() && SetConsoleCP(65001).is_ok()) }
}
