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

#[pyfunction]
pub fn set_utility_window(hwnd_val: usize, enable: bool) -> PyResult<()> {
    let ns_window = hwnd_val as id;
    unsafe {
        let style_mask: usize = msg_send![ns_window, styleMask];
        let utility_mask = 1 << 4; // NSWindowStyleMaskUtilityWindow
        let new_style = if enable { style_mask | utility_mask } else { style_mask & !utility_mask };
        let _: () = msg_send![ns_window, setStyleMask: new_style];

        // NSApplicationActivationPolicyAccessory = 1, Regular = 0
        let ns_app: id = msg_send![class!(NSApplication), sharedApplication];
        let policy = if enable { 1_isize } else { 0_isize };
        let _: () = msg_send![ns_app, setActivationPolicy: policy];
    }
    Ok(())
}

#[pyfunction]
pub fn make_frameless(hwnd_val: usize) -> PyResult<()> {
    let ns_window = hwnd_val as id;
    unsafe {
        let _: () = msg_send![ns_window, setStyleMask: 32783_usize];
        let _: () = msg_send![ns_window, setTitlebarAppearsTransparent: 1_i8];
        let _: () = msg_send![ns_window, setTitleVisibility: 1_isize];
    }
    Ok(())
}

#[pyfunction]
pub fn set_launch_on_boot(app_name: String, exe_path: String, enable: bool) -> PyResult<bool> {
    use std::fs;
    use std::path::PathBuf;

    let home = std::env::var("HOME").map(PathBuf::from)
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Could not find HOME directory"))?;
    let launch_agents = home.join("Library/LaunchAgents");
    let plist_file = launch_agents.join(format!("com.{}.startup.plist", app_name.to_lowercase()));

    if enable {
        let _ = fs::create_dir_all(&launch_agents);
        let args: Vec<&str> = if exe_path.starts_with('"') && exe_path.ends_with('"') {
            vec![&exe_path[1..exe_path.len() - 1]]
        } else {
            exe_path.split_whitespace().collect()
        };
        let array_items: String = args.iter()
            .map(|arg| format!("        <string>{}</string>", arg))
            .collect::<Vec<_>>()
            .join("\n");
        let content = format!(
            r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{}.startup</string>
    <key>ProgramArguments</key>
    <array>
{}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"#,
            app_name.to_lowercase(),
            array_items
        );
        fs::write(plist_file, content)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    } else if plist_file.exists() {
        let _ = fs::remove_file(plist_file);
    }
    Ok(true)
}
