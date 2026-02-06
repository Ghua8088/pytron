use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::{Arc, Mutex, Once};
use tao::event_loop::EventLoopProxy;
use crate::events::UserEvent;
use crate::utils::SendWrapper;

// --- THE STATIC AUTHORITY ---
// These globals ensure that every NativeState instance in the process
// shares the exact same underlying storage.
static mut GLOBAL_DATA: Option<Arc<Mutex<HashMap<String, Py<PyAny>>>>> = None;
static mut GLOBAL_PROXY: Option<Arc<Mutex<Option<SendWrapper<EventLoopProxy<UserEvent>>>>>> = None;
static INIT: Once = Once::new();

fn get_global_data() -> Arc<Mutex<HashMap<String, Py<PyAny>>>> {
    unsafe {
        INIT.call_once(|| {
            GLOBAL_DATA = Some(Arc::new(Mutex::new(HashMap::new())));
            GLOBAL_PROXY = Some(Arc::new(Mutex::new(None)));
        });
        GLOBAL_DATA.as_ref().unwrap().clone()
    }
}

fn get_global_proxy() -> Arc<Mutex<Option<SendWrapper<EventLoopProxy<UserEvent>>>>> {
    unsafe {
        INIT.call_once(|| {
            GLOBAL_DATA = Some(Arc::new(Mutex::new(HashMap::new())));
            GLOBAL_PROXY = Some(Arc::new(Mutex::new(None)));
        });
        GLOBAL_PROXY.as_ref().unwrap().clone()
    }
}

#[pyclass]
#[derive(Clone)]
pub struct NativeState {
    // These fields are just handles to the static globals
    data: Arc<Mutex<HashMap<String, Py<PyAny>>>>,
    proxy: Arc<Mutex<Option<SendWrapper<EventLoopProxy<UserEvent>>>>>,
}

#[pymethods]
impl NativeState {
    #[new]
    pub fn new() -> Self {
        // Always attach to the SINGLETON authority
        NativeState {
            data: get_global_data(),
            proxy: get_global_proxy(),
        }
    }

    pub fn set(&self, py: Python<'_>, key: String, value: Py<PyAny>) {
        let mut data = self.data.lock().unwrap();
        // println!("[SHIELD] Rust Singleton: {} updated", key);
        data.insert(key.clone(), value.clone_ref(py));
        
        // --- IRON BRIDGE: NATIVE PROPAGATION ---
        if let Ok(proxy_lock) = self.proxy.lock() {
            if let Some(wrapped_proxy) = proxy_lock.as_ref() {
                let proxy = wrapped_proxy.0.clone();
                let mut json_val = String::from("null");
                if let Ok(json_mod) = py.import_bound("json") {
                    if let Ok(res) = json_mod.call_method1("dumps", (value,)) {
                        if let Ok(s) = res.extract::<String>() { json_val = s; }
                    }
                }
                let _ = proxy.send_event(UserEvent::StateUpdate(key, json_val));
            }
        }
    }

    pub fn get(&self, py: Python<'_>, key: String) -> Option<Py<PyAny>> {
        let data = self.data.lock().unwrap();
        data.get(&key).map(|v| v.clone_ref(py))
    }

    pub fn to_dict(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let data = self.data.lock().unwrap();
        let dict = PyDict::new(py);
        for (k, v) in data.iter() {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    pub fn update(&self, py: Python<'_>, mapping: Bound<'_, PyDict>) -> PyResult<()> {
        let mut data = self.data.lock().unwrap();
        for (k, v) in mapping.iter() {
            let key = k.extract::<String>()?;
            let val = v.unbind();
            
            if let Ok(proxy_lock) = self.proxy.lock() {
                if let Some(wrapped_proxy) = proxy_lock.as_ref() {
                    let proxy = wrapped_proxy.0.clone();
                    let mut json_val = String::from("null");
                    if let Ok(json_mod) = py.import_bound("json") {
                        if let Ok(res) = json_mod.call_method1("dumps", (val.clone_ref(py),)) {
                            if let Ok(s) = res.extract::<String>() { json_val = s; }
                        }
                    }
                    let _ = proxy.send_event(UserEvent::StateUpdate(key.clone(), json_val));
                }
            }
            data.insert(key, val);
        }
        Ok(())
    }

    pub fn keys(&self) -> Vec<String> {
        let data = self.data.lock().unwrap();
        data.keys().cloned().collect()
    }
}

// Internal Rust API
impl NativeState {
    pub fn _bind_proxy(&self, proxy: EventLoopProxy<UserEvent>) {
        if let Ok(mut lock) = self.proxy.lock() {
            *lock = Some(SendWrapper::new(proxy));
        }
    }
}
