use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use pyo3::prelude::*;
use wry::WebView;
use tao::window::Window;
#[cfg(not(target_os = "android"))]
use tray_icon::TrayIcon;

use crate::store::NativeState;

pub struct RuntimeState {
    pub webview: WebView,
    pub window: Window,
    pub callbacks: Arc<Mutex<HashMap<String, PyObject>>>,
    #[cfg(not(target_os = "android"))]
    pub tray: Option<TrayIcon>,
    pub prevent_close: bool,
    pub is_utility: bool,
    pub store: NativeState,
}