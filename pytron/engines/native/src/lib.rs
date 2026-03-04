use pyo3::prelude::*;

pub mod events;
pub mod state;
pub mod utils;
pub mod protocol;
pub mod webview;
pub mod ipc;
pub mod store;

use crate::webview::NativeWebview;
use crate::ipc::ChromeIPC;
use crate::store::NativeState;

#[pymodule]
fn pytron_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<NativeWebview>()?;
    m.add_class::<ChromeIPC>()?;
    m.add_class::<NativeState>()?;
    Ok(())
}
