use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use pyo3::prelude::*;
use wry::WebView;
use tao::window::Window;
use tray_icon::TrayIcon;

use crate::store::NativeState;

pub struct RuntimeState {
    pub webview: WebView,
    pub window: Window,
    pub callbacks: Arc<Mutex<HashMap<String, PyObject>>>,
    pub tray: Option<TrayIcon>,
    pub prevent_close: bool,
    pub store: NativeState,
}
