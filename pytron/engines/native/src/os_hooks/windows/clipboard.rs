use pyo3::prelude::*;
use arboard::Clipboard;

#[pyfunction]
pub fn set_clipboard_text(text: String) -> PyResult<bool> {
    if let Ok(mut clipboard) = Clipboard::new() {
        let _ = clipboard.set_text(text);
        Ok(true)
    } else {
        Ok(false)
    }
}

#[pyfunction]
pub fn get_clipboard_text() -> PyResult<Option<String>> {
    if let Ok(mut clipboard) = Clipboard::new() {
        Ok(clipboard.get_text().ok())
    } else {
        Ok(None)
    }
}
