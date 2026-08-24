use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::{Arc, Mutex, OnceLock};
use tao::event_loop::EventLoopProxy;
use crate::events::UserEvent;
use crate::utils::SendWrapper;

// --- THE STATIC AUTHORITY ---
// These globals ensure that every NativeState instance in the process
// shares the exact same underlying storage.
static GLOBAL_DATA: OnceLock<Arc<Mutex<HashMap<String, Py<PyAny>>>>> = OnceLock::new();
static GLOBAL_PROXIES: OnceLock<Arc<Mutex<Vec<SendWrapper<EventLoopProxy<UserEvent>>>>>> = OnceLock::new();

fn get_global_data() -> Arc<Mutex<HashMap<String, Py<PyAny>>>> {
    GLOBAL_DATA.get_or_init(|| Arc::new(Mutex::new(HashMap::new()))).clone()
}

fn get_global_proxies() -> Arc<Mutex<Vec<SendWrapper<EventLoopProxy<UserEvent>>>>> {
    GLOBAL_PROXIES.get_or_init(|| Arc::new(Mutex::new(Vec::new()))).clone()
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
        // Serialize before acquiring the proxies lock to minimize lock contention.
        if let Ok(mut proxies_lock) = self.proxies.lock() {
            if !proxies_lock.is_empty() {
                let mut json_val = String::from("null");
                if let Ok(json_mod) = py.import("json") {
                    if let Ok(res) = json_mod.call_method1("dumps", (value,)) {
                        if let Ok(s) = res.extract::<String>() { json_val = s; }
                    }
                }
                
                // FIX: prune stale proxies (from closed windows) as we broadcast.
                // `send_event` fails when the event loop has been dropped, so we
                // remove those entries to prevent unbounded Vec growth.
                proxies_lock.retain(|wrapped_proxy| {
                    wrapped_proxy.0.send_event(UserEvent::StateUpdate(key.clone(), json_val.clone())).is_ok()
                });
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
        // --- LOCK ORDERING FIX ---
        // We must NOT hold `self.data` while calling into Python (json.dumps),
        // because Python code can re-enter NativeState::get/set which also lock
        // `self.data`, deadlocking the process.
        //
        // Strategy:
        //   1. Collect (key, val) pairs while briefly holding the data lock.
        //   2. Release the data lock.
        //   3. Serialize all values to JSON (Python call, no Rust lock held).
        //   4. Re-acquire the data lock to insert everything at once.
        //   5. Broadcast to proxies (pruning dead ones).

        // Step 1: collect all pairs from the PyDict (mapping is a borrowed Python object,
        // so the GIL is already held here — no extra locking needed for extraction).
        let mut pairs: Vec<(String, Py<PyAny>)> = Vec::new();
        for (k, v) in mapping.iter() {
            let key = k.extract::<String>()?;
            let val = v.unbind();
            pairs.push((key, val));
        }

        // Step 2 & 3: Serialize values to JSON while holding NO Rust locks.
        let mut serialized: Vec<(String, Py<PyAny>, String)> = Vec::with_capacity(pairs.len());
        for (key, val) in pairs {
            let mut json_val = String::from("null");
            if let Ok(json_mod) = py.import("json") {
                if let Ok(res) = json_mod.call_method1("dumps", (val.clone_ref(py),)) {
                    if let Ok(s) = res.extract::<String>() { json_val = s; }
                }
            }
            serialized.push((key, val, json_val));
        }

        // Step 4: Re-acquire data lock and insert all values at once.
        {
            let mut data = self.data.lock().unwrap();
            for (key, val, _) in &serialized {
                data.insert(key.clone(), val.clone_ref(py));
            }
        } // data lock released here

        // Step 5: Broadcast state updates to all living event loops.
        if let Ok(mut proxies_lock) = self.proxies.lock() {
            if !proxies_lock.is_empty() {
                // Collect all (key, json) pairs that need to be broadcast.
                // We do the broadcast in a single pass and prune dead proxies.
                let updates: Vec<(String, String)> = serialized
                    .iter()
                    .map(|(k, _, j)| (k.clone(), j.clone()))
                    .collect();

                proxies_lock.retain(|wrapped_proxy| {
                    // A proxy is considered alive if at least one send succeeds.
                    // We send all updates and only prune if EVERY send fails.
                    let mut alive = false;
                    for (key, json_val) in &updates {
                        if wrapped_proxy.0.send_event(UserEvent::StateUpdate(key.clone(), json_val.clone())).is_ok() {
                            alive = true;
                        }
                    }
                    alive || updates.is_empty()
                });
            }
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