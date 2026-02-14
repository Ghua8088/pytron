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
static mut GLOBAL_PROXIES: Option<Arc<Mutex<Vec<SendWrapper<EventLoopProxy<UserEvent>>>>>> = None;
static INIT: Once = Once::new();

fn get_global_data() -> Arc<Mutex<HashMap<String, Py<PyAny>>>> {
    unsafe {
        INIT.call_once(|| {
            GLOBAL_DATA = Some(Arc::new(Mutex::new(HashMap::new())));
            GLOBAL_PROXIES = Some(Arc::new(Mutex::new(Vec::new())));
        });
        GLOBAL_DATA.as_ref().unwrap().clone()
    }
}

fn get_global_proxies() -> Arc<Mutex<Vec<SendWrapper<EventLoopProxy<UserEvent>>>>> {
    unsafe {
        INIT.call_once(|| {
            GLOBAL_DATA = Some(Arc::new(Mutex::new(HashMap::new())));
            GLOBAL_PROXIES = Some(Arc::new(Mutex::new(Vec::new())));
        });
        GLOBAL_PROXIES.as_ref().unwrap().clone()
    }
}

#[pyclass]
#[derive(Clone)]
pub struct NativeState {
    // These fields are just handles to the static globals
    data: Arc<Mutex<HashMap<String, Py<PyAny>>>>,
    proxies: Arc<Mutex<Vec<SendWrapper<EventLoopProxy<UserEvent>>>>>,
}

#[pymethods]
impl NativeState {
    #[new]
    pub fn new() -> Self {
        // Always attach to the SINGLETON authority
        NativeState {
            data: get_global_data(),
            proxies: get_global_proxies(),
        }
    }

    pub fn set(&self, py: Python<'_>, key: String, value: Py<PyAny>) {
        let mut data = self.data.lock().unwrap();
        data.insert(key.clone(), value.clone_ref(py));
        
        // --- IRON BRIDGE: NATIVE PROPAGATION (BROADCAST) ---
        if let Ok(proxies_lock) = self.proxies.lock() {
            if !proxies_lock.is_empty() {
                let mut json_val = String::from("null");
                if let Ok(json_mod) = py.import_bound("json") {
                    if let Ok(res) = json_mod.call_method1("dumps", (value,)) {
                        if let Ok(s) = res.extract::<String>() { json_val = s; }
                    }
                }
                
                for wrapped_proxy in proxies_lock.iter() {
                    let _ = wrapped_proxy.0.send_event(UserEvent::StateUpdate(key.clone(), json_val.clone()));
                }
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
        let proxies_opt = self.proxies.lock().ok();

        for (k, v) in mapping.iter() {
            let key = k.extract::<String>()?;
            let val = v.unbind();
            
            if let Some(proxies_lock) = proxies_opt.as_ref() {
                if !proxies_lock.is_empty() {
                    let mut json_val = String::from("null");
                    if let Ok(json_mod) = py.import_bound("json") {
                        if let Ok(res) = json_mod.call_method1("dumps", (val.clone_ref(py),)) {
                            if let Ok(s) = res.extract::<String>() { json_val = s; }
                        }
                    }
                    for wrapped_proxy in proxies_lock.iter() {
                        let _ = wrapped_proxy.0.send_event(UserEvent::StateUpdate(key.clone(), json_val.clone()));
                    }
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
        if let Ok(mut lock) = self.proxies.lock() {
            lock.push(SendWrapper::new(proxy));
        }
    }
}