use pyo3::prelude::*;

/// Linux / macOS terminals are UTF-8 by default; nothing to set.
#[pyfunction]
pub fn set_console_utf8() -> PyResult<bool> {
    Ok(true)
}
