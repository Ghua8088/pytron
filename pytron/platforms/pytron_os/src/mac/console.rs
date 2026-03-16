use pyo3::prelude::*;

/// macOS / Unix terminals default to UTF-8; nothing to do.
#[pyfunction]
pub fn set_console_utf8() -> PyResult<bool> {
    Ok(true)
}
