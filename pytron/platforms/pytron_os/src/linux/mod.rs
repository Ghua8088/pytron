pub mod clipboard;
pub mod console;
pub mod dialogs;
pub mod hotkeys;
pub mod msgloop;
pub mod tray;
pub mod window;

pub use clipboard::*;
pub use console::*;
pub use dialogs::*;
pub use hotkeys::*;
pub use msgloop::*;
pub use tray::*;
pub use window::*;

// Dynamically linked via tao's bundled GTK3
extern "C" {
    fn gtk_window_set_skip_taskbar_hint(window: *mut c_void, setting: c_int);
    fn gtk_window_set_decorated(window: *mut c_void, setting: c_int);
}

#[pyfunction]
pub fn set_utility_window(hwnd_val: usize, enable: bool) -> PyResult<()> {
    let gtk_window = hwnd_val as *mut c_void;
    unsafe { gtk_window_set_skip_taskbar_hint(gtk_window, if enable { 1 } else { 0 }); }
    Ok(())
}

#[pyfunction]
pub fn make_frameless(hwnd_val: usize) -> PyResult<()> {
    let gtk_window = hwnd_val as *mut c_void;
    unsafe { gtk_window_set_decorated(gtk_window, 0); }
    Ok(())
}

#[pyfunction]
pub fn set_launch_on_boot(app_name: String, exe_path: String, enable: bool) -> PyResult<bool> {
    use std::fs;
    use std::path::PathBuf;

    let home = std::env::var("HOME").map(PathBuf::from)
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Could not find HOME directory"))?;
    let autostart_dir = home.join(".config/autostart");
    let desktop_file = autostart_dir.join(format!("{}.desktop", app_name));

    if enable {
        let _ = fs::create_dir_all(&autostart_dir);
        let content = format!(
            "[Desktop Entry]\nType=Application\nName={}\nExec={}\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\n",
            app_name, exe_path
        );
        fs::write(desktop_file, content)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    } else if desktop_file.exists() {
        let _ = fs::remove_file(desktop_file);
    }
    Ok(true)
}
