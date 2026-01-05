use pyo3::prelude::*;
use pyo3::types::PyList;
use std::env;
use std::path::{Path, PathBuf};
use std::fs;
use crate::security::decrypt_payload;

pub fn find_internal_dir() -> (PathBuf, PathBuf) {
    let exe_path = env::current_exe().unwrap_or_else(|_| PathBuf::from("app.exe"));
    let root_dir = exe_path.parent().unwrap_or_else(|| Path::new(".")).to_path_buf();
    let internal_dir = root_dir.join("_internal");
    
    if internal_dir.exists() {
        (root_dir, internal_dir)
    } else {
        (root_dir.clone(), root_dir)
    }
}

pub fn run_python_and_payload(root_dir: &Path, internal_dir: &Path, base_zip: &Path) -> PyResult<()> {
    pyo3::prepare_freethreaded_python();

    let exe_path = env::current_exe().map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("EXE check failed: {}", e)))?;
    
    Python::with_gil(|py| {
        let sys = py.import_bound("sys")?;
        let os = py.import_bound("os")?;

        sys.setattr("frozen", true)?;
        sys.setattr("_MEIPASS", internal_dir.to_string_lossy())?;
        sys.setattr("executable", exe_path.to_string_lossy())?;

        if cfg!(windows) {
            let internal_str = internal_dir.to_string_lossy();
            if let Ok(add_dll_func) = os.getattr("add_dll_directory") {
                let _ = add_dll_func.call1((internal_str,));
            }
        }

        let path_list: Bound<PyList> = sys.getattr("path")?.extract()?;
        let base_str = base_zip.to_string_lossy();
        let int_str = internal_dir.to_string_lossy();
        
        if !path_list.contains(&base_str)? {
            path_list.insert(0, base_str)?;
        }
        if !path_list.contains(&int_str)? {
            path_list.insert(1, int_str)?;
        }

        // --- CLI Argument Forwarding ---
        let args: Vec<String> = env::args().collect();
        let py_args = PyList::new_bound(py, &args);
        sys.setattr("argv", py_args)?;

        // Load and decrypt payload from the verified root directory
        let payload_path = root_dir.join("app.pytron");

        let encrypted_data = fs::read(&payload_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to read app.pytron at {:?}: {}", payload_path, e)))?;
        
        match decrypt_payload(&encrypted_data) {
            Ok(decrypted_code) => {
                let namespace = pyo3::types::PyDict::new_bound(py);
                namespace.set_item("__name__", "__main__")?;
                namespace.set_item("__file__", payload_path.to_string_lossy())?;
                
                let builtins = py.import_bound("builtins")?;
                namespace.set_item("__builtins__", builtins)?;
                
                py.run_bound(&decrypted_code, Some(&namespace), Some(&namespace))?;
            },
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Integrity Violation: {} (Key may be mismatched)", e)
                ));
            }
        }
        
        Ok(())
    })
}
