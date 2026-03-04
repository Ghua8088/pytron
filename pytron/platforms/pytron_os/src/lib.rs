use pyo3::prelude::*;

#[cfg(target_os = "windows")]
mod win {
    use pyo3::prelude::*;
    use windows::Win32::Foundation::{HWND, RECT, WPARAM, LPARAM, LRESULT};
    use windows::Win32::UI::WindowsAndMessaging::{
        GetWindowLongW, SetWindowLongW, SetWindowPos, GWL_EXSTYLE, GWL_STYLE, 
        WS_EX_TOOLWINDOW, WS_EX_APPWINDOW, SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER, SWP_FRAMECHANGED,
        WS_CAPTION, SWP_NOACTIVATE, SW_MINIMIZE, SW_MAXIMIZE, SW_RESTORE, SW_HIDE, SW_SHOW,
        ShowWindow, IsZoomed, PostMessageW, SendMessageW, IsWindowVisible, SetForegroundWindow,
        GetWindowRect, GetSystemMetrics, WM_CLOSE, WM_NCLBUTTONDOWN, HTCAPTION,
        SM_CXSCREEN, SM_CYSCREEN, HWND_TOPMOST, HWND_NOTOPMOST
    };
    use windows::Win32::System::Com::{CoCreateInstance, CoInitialize, CLSCTX_INPROC_SERVER};
    use windows::Win32::UI::Shell::{ITaskbarList, TaskbarList};
    use windows::Win32::UI::Input::KeyboardAndMouse::ReleaseCapture;

    #[pyfunction]
    pub fn set_utility_window(hwnd_val: usize, enable: bool) -> PyResult<()> {
        let hwnd = HWND(hwnd_val as isize);
        unsafe {
            // Modify EXSTYLE (still needed for Alt-Tab hiding and border modes)
            let mut ex_style = GetWindowLongW(hwnd, GWL_EXSTYLE);
            if enable {
                ex_style = (ex_style | WS_EX_TOOLWINDOW.0 as i32) & !(WS_EX_APPWINDOW.0 as i32);
            } else {
                ex_style = (ex_style | WS_EX_APPWINDOW.0 as i32) & !(WS_EX_TOOLWINDOW.0 as i32);
            }
            SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style);
            let _ = SetWindowPos(hwnd, HWND::default(), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED | SWP_NOACTIVATE);

            // Dynamically strip it from the taskbar using COM (Works completely seamlessly)
            let _ = CoInitialize(None); // Ok if it fails
            if let Ok(taskbar) = CoCreateInstance::<_, ITaskbarList>(&TaskbarList, None, CLSCTX_INPROC_SERVER) {
                if taskbar.HrInit().is_ok() {
                    if enable {
                        let _ = taskbar.DeleteTab(hwnd);
                    } else {
                        let _ = taskbar.AddTab(hwnd);
                    }
                }
            }
        }
        Ok(())
    }

    #[pyfunction]
    pub fn make_frameless(hwnd_val: usize) -> PyResult<()> {
        let hwnd = HWND(hwnd_val as isize);
        unsafe {
            let style = GetWindowLongW(hwnd, GWL_STYLE);
            let new_style = style & !(WS_CAPTION.0 as i32);
            SetWindowLongW(hwnd, GWL_STYLE, new_style);
            let _ = SetWindowPos(hwnd, HWND::default(), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED);
        }
        Ok(())
    }

    #[pyfunction]
    pub fn minimize(hwnd_val: usize) -> PyResult<()> {
        let hwnd = HWND(hwnd_val as isize);
        unsafe { let _ = ShowWindow(hwnd, SW_MINIMIZE); }
        Ok(())
    }

    #[pyfunction]
    pub fn set_bounds(hwnd_val: usize, x: i32, y: i32, width: i32, height: i32) -> PyResult<()> {
        let hwnd = HWND(hwnd_val as isize);
        unsafe { let _ = SetWindowPos(hwnd, HWND::default(), x, y, width, height, SWP_NOZORDER | SWP_NOACTIVATE); }
        Ok(())
    }

    #[pyfunction]
    pub fn close(hwnd_val: usize) -> PyResult<()> {
        let hwnd = HWND(hwnd_val as isize);
        unsafe { let _ = PostMessageW(hwnd, WM_CLOSE, WPARAM(0), LPARAM(0)); }
        Ok(())
    }

    #[pyfunction]
    pub fn toggle_maximize(hwnd_val: usize) -> PyResult<bool> {
        let hwnd = HWND(hwnd_val as isize);
        unsafe {
            let is_zoomed = IsZoomed(hwnd).as_bool();
            if is_zoomed {
                let _ = ShowWindow(hwnd, SW_RESTORE);
                Ok(false)
            } else {
                let _ = ShowWindow(hwnd, SW_MAXIMIZE);
                Ok(true)
            }
        }
    }

    #[pyfunction]
    pub fn set_always_on_top(hwnd_val: usize, enable: bool) -> PyResult<()> {
        let hwnd = HWND(hwnd_val as isize);
        let insert_after = if enable { HWND_TOPMOST } else { HWND_NOTOPMOST };
        unsafe { let _ = SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE); }
        Ok(())
    }

    #[pyfunction]
    pub fn start_drag(hwnd_val: usize) -> PyResult<()> {
        let hwnd = HWND(hwnd_val as isize);
        unsafe {
            let _ = ReleaseCapture();
            let _ = SendMessageW(hwnd, WM_NCLBUTTONDOWN, WPARAM(HTCAPTION as usize), LPARAM(0));
        }
        Ok(())
    }

    #[pyfunction]
    pub fn hide(hwnd_val: usize) -> PyResult<()> {
        let hwnd = HWND(hwnd_val as isize);
        unsafe { let _ = ShowWindow(hwnd, SW_HIDE); }
        Ok(())
    }

    #[pyfunction]
    pub fn is_visible(hwnd_val: usize) -> PyResult<bool> {
        let hwnd = HWND(hwnd_val as isize);
        unsafe { Ok(IsWindowVisible(hwnd).as_bool()) }
    }

    #[pyfunction]
    pub fn show(hwnd_val: usize) -> PyResult<()> {
        let hwnd = HWND(hwnd_val as isize);
        unsafe {
            let _ = ShowWindow(hwnd, SW_SHOW);
            let _ = SetForegroundWindow(hwnd);
        }
        Ok(())
    }

    #[pyfunction]
    pub fn center(hwnd_val: usize) -> PyResult<()> {
        let hwnd = HWND(hwnd_val as isize);
        unsafe {
            let mut rect = RECT::default();
            if GetWindowRect(hwnd, &mut rect).is_ok() {
                let width = rect.right - rect.left;
                let height = rect.bottom - rect.top;
                let screen_w = GetSystemMetrics(SM_CXSCREEN);
                let screen_h = GetSystemMetrics(SM_CYSCREEN);
                let x = (screen_w - width) / 2;
                let y = (screen_h - height) / 2;
                let _ = SetWindowPos(hwnd, HWND::default(), x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER);
            }
        }
        Ok(())
    }

    #[pyfunction]
    pub fn set_launch_on_boot(app_name: String, exe_path: String, enable: bool) -> PyResult<bool> {
        use windows::Win32::System::Registry::{
            RegCloseKey, RegCreateKeyExW, RegDeleteValueW, RegSetValueExW, HKEY_CURRENT_USER,
            KEY_SET_VALUE, REG_SZ,
        };
        use windows::core::PCWSTR;

        let sub_key = "Software\\Microsoft\\Windows\\CurrentVersion\\Run\0";
        let sub_key_u16: Vec<u16> = sub_key.encode_utf16().collect();
        let app_name_u16: Vec<u16> = format!("{}\0", app_name).encode_utf16().collect();

        unsafe {
            let mut hkey = windows::Win32::System::Registry::HKEY::default();
            if RegCreateKeyExW(
                HKEY_CURRENT_USER,
                PCWSTR(sub_key_u16.as_ptr()),
                0,
                PCWSTR::null(),
                windows::Win32::System::Registry::REG_OPTION_NON_VOLATILE,
                KEY_SET_VALUE,
                None,
                &mut hkey,
                None,
            )
            .is_ok()
            {
                if enable {
                    let exe_path_u16: Vec<u16> = format!("{}\0", exe_path).encode_utf16().collect();
                    let _ = RegSetValueExW(
                        hkey,
                        PCWSTR(app_name_u16.as_ptr()),
                        0,
                        REG_SZ,
                        Some(std::slice::from_raw_parts(
                            exe_path_u16.as_ptr() as *const u8,
                            exe_path_u16.len() * 2,
                        )),
                    );
                } else {
                    let _ = RegDeleteValueW(hkey, PCWSTR(app_name_u16.as_ptr()));
                }
                let _ = RegCloseKey(hkey);
                Ok(true)
            } else {
                Ok(false)
            }
        }
    }
}

#[cfg(target_os = "macos")]
mod mac {
    use pyo3::prelude::*;
    use objc::{class, msg_send, sel, sel_impl};
    use cocoa::base::id;

    #[pyfunction]
    pub fn set_utility_window(hwnd_val: usize, enable: bool) -> PyResult<()> {
        let ns_window = hwnd_val as id;
        unsafe {
            let style_mask: usize = msg_send![ns_window, styleMask];
            let utility_mask = 1 << 4; // NSWindowStyleMaskUtilityWindow
            
            let new_style = if enable {
                style_mask | utility_mask
            } else {
                style_mask & !utility_mask
            };
            let _: () = msg_send![ns_window, setStyleMask: new_style];
            
            // Hide the application dock icon via Activation Policy
            // NSApplicationActivationPolicyAccessory = 1
            // NSApplicationActivationPolicyRegular = 0
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
            let _: () = msg_send![ns_window, setTitlebarAppearsTransparent: 1_i8]; // BOOL as i8
            let _: () = msg_send![ns_window, setTitleVisibility: 1_isize];
        }
        Ok(())
    }

    #[pyfunction]
    pub fn set_launch_on_boot(app_name: String, exe_path: String, enable: bool) -> PyResult<bool> {
        use std::fs;
        use std::path::PathBuf;

        let home = std::env::var("HOME").map(PathBuf::from).map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Could not find HOME directory"))?;
        let launch_agents = home.join("Library/LaunchAgents");
        let plist_file = launch_agents.join(format!("com.{}.startup.plist", app_name.to_lowercase()));

        if enable {
            let _ = fs::create_dir_all(&launch_agents);
            // Split exe_path simple way (since it's usually quoted or plain)
            let args: Vec<&str> = if exe_path.starts_with('"') && exe_path.ends_with('"') {
                vec![&exe_path[1..exe_path.len()-1]]
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

            fs::write(plist_file, content).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        } else if plist_file.exists() {
            let _ = fs::remove_file(plist_file);
        }
        Ok(true)
    }
}

#[cfg(target_os = "linux")]
mod linux {
    use pyo3::prelude::*;
    use std::os::raw::{c_int, c_void};
    
    // We dynamically link these at runtime since Linux guarantees Gtk3 inside `tao`
    extern "C" {
        fn gtk_window_set_skip_taskbar_hint(window: *mut c_void, setting: c_int);
        fn gtk_window_set_decorated(window: *mut c_void, setting: c_int);
    }

    #[pyfunction]
    pub fn set_utility_window(hwnd_val: usize, enable: bool) -> PyResult<()> {
        let gtk_window = hwnd_val as *mut c_void;
        unsafe {
            gtk_window_set_skip_taskbar_hint(gtk_window, if enable { 1 } else { 0 });
        }
        Ok(())
    }

    #[pyfunction]
    pub fn make_frameless(hwnd_val: usize) -> PyResult<()> {
        let gtk_window = hwnd_val as *mut c_void;
        unsafe {
            gtk_window_set_decorated(gtk_window, 0);
        }
        Ok(())
    }

    #[pyfunction]
    pub fn set_launch_on_boot(app_name: String, exe_path: String, enable: bool) -> PyResult<bool> {
        use std::fs;
        use std::path::PathBuf;

        let home = std::env::var("HOME").map(PathBuf::from).map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Could not find HOME directory"))?;
        let autostart_dir = home.join(".config/autostart");
        let desktop_file = autostart_dir.join(format!("{}.desktop", app_name));

        if enable {
            let _ = fs::create_dir_all(&autostart_dir);
            let content = format!(
                r#"[Desktop Entry]
Type=Application
Name={}
Exec={}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"#,
                app_name, exe_path
            );
            fs::write(desktop_file, content).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        } else if desktop_file.exists() {
            let _ = fs::remove_file(desktop_file);
        }
        Ok(true)
    }
}

#[pymodule]
fn pytron_os(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    #[cfg(target_os = "windows")]
    {
        m.add_function(wrap_pyfunction!(win::set_utility_window, m)?)?;
        m.add_function(wrap_pyfunction!(win::make_frameless, m)?)?;
        m.add_function(wrap_pyfunction!(win::minimize, m)?)?;
        m.add_function(wrap_pyfunction!(win::set_bounds, m)?)?;
        m.add_function(wrap_pyfunction!(win::close, m)?)?;
        m.add_function(wrap_pyfunction!(win::toggle_maximize, m)?)?;
        m.add_function(wrap_pyfunction!(win::set_always_on_top, m)?)?;
        m.add_function(wrap_pyfunction!(win::start_drag, m)?)?;
        m.add_function(wrap_pyfunction!(win::hide, m)?)?;
        m.add_function(wrap_pyfunction!(win::is_visible, m)?)?;
        m.add_function(wrap_pyfunction!(win::show, m)?)?;
        m.add_function(wrap_pyfunction!(win::center, m)?)?;
        m.add_function(wrap_pyfunction!(win::set_launch_on_boot, m)?)?;
    }
    
    #[cfg(target_os = "macos")]
    {
        m.add_function(wrap_pyfunction!(mac::set_utility_window, m)?)?;
        m.add_function(wrap_pyfunction!(mac::make_frameless, m)?)?;
        m.add_function(wrap_pyfunction!(mac::set_launch_on_boot, m)?)?;
    }

    #[cfg(target_os = "linux")]
    {
        m.add_function(wrap_pyfunction!(linux::set_utility_window, m)?)?;
        m.add_function(wrap_pyfunction!(linux::make_frameless, m)?)?;
        m.add_function(wrap_pyfunction!(linux::set_launch_on_boot, m)?)?;
    }
    
    Ok(())
}
