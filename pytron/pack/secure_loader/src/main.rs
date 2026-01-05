#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod security;
mod config;
mod patcher;
mod ui;
mod python_runtime;

use pyo3::prelude::*;
use std::env;
use crate::security::{check_debugger, get_footer_data};
use crate::config::load_settings;
use crate::patcher::check_and_apply_patches;
use crate::ui::{alert, init_com, set_app_id};
use crate::python_runtime::{find_internal_dir, run_python_and_payload};

fn main() -> PyResult<()> {
    // 1. CLI Argument Parsing and Console Allocation
    let args: Vec<String> = env::args().collect();
    let debug_mode = args.iter().any(|arg| arg == "--debug");

    if debug_mode {
        #[cfg(windows)]
        unsafe {
            if let Ok(func) = libloading::Library::new("kernel32.dll") {
                 let alloc: libloading::Symbol<unsafe extern "system" fn() -> i32> = func.get(b"AllocConsole").unwrap();
                 alloc();
            }
        }
    }

    // 2. Anti-Debugging & COM Init
    check_debugger();
    init_com();

    let (root_dir, internal_dir) = find_internal_dir();
    
    check_and_apply_patches(&root_dir);

    // Verify critical files (Payload only)
    let payload_path = root_dir.join("app.pytron");

    if !payload_path.exists() {
        alert("Shield: Discovery Error", &format!(
            "Critical asset 'app.pytron' missing.\nChecked: {}\n\nDistribution may be corrupted.",
            payload_path.display()
        ));
        std::process::exit(1);
    }

    // Verify Integrity (Check Footer presence)
    if let Err(e) = get_footer_data() {
         alert("Security Alert", &format!("Integrity check failed: {}", e));
         std::process::exit(1);
    }
    
    // Load config from settings.json on disk (Standard)
    let settings = load_settings(&root_dir, None);
    let app_title = settings.as_ref().and_then(|s| s.title.clone()).unwrap_or_else(|| "Pytron App".to_string());
    
    // Set App ID for Task Manager grouping
    let app_id = format!("Pytron.{}.{}", 
        settings.as_ref().and_then(|s| s.author.clone()).unwrap_or_else(|| "User".to_string()).replace(" ", ""),
        app_title.replace(" ", "")
    );
    set_app_id(&app_id);
    
    let base_zip = internal_dir.join("base_library.zip");

    // 2. Strict Environment Isolation
    // Clear inherited Python variables that might poison the runtime
    env::remove_var("PYTHONPATH");
    env::remove_var("PYTHONHOME");
    
    env::set_var("PYTHONHOME", &internal_dir);
    
    let path_sep = if cfg!(windows) { ";" } else { ":" };
    let python_path = format!("{}{}{}", base_zip.display(), path_sep, internal_dir.display());
    
    env::set_var("PYTHONPATH", &python_path);
    env::set_var("PYTHONNOUSERSITE", "1");
    // Force UTF-8 Mode for Python 3.10+
    env::set_var("PYTHONUTF8", "1");

    // Run execution
    let res = run_python_and_payload(&root_dir, &internal_dir, &base_zip);
    if let Err(e) = res {
        alert(&app_title, &format!("Fatal Engine Error:\n{}", e));
    }
    Ok(())
}
