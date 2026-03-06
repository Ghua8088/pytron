use pyo3::prelude::*;
use objc::{class, msg_send, sel, sel_impl};
use cocoa::base::{id, nil};

// ─── Helpers ─────────────────────────────────────────────────────────────────

unsafe fn nsstring(s: &str) -> id {
    let bytes = s.as_bytes();
    let ns: id = msg_send![class!(NSString), alloc];
    msg_send![ns, initWithBytes:bytes.as_ptr() length:bytes.len() encoding:4u64] // NSUTF8StringEncoding
}

// ─── Window management ───────────────────────────────────────────────────────

#[pyfunction]
pub fn set_utility_window(hwnd_val: usize, enable: bool) -> PyResult<()> {
    let ns_win = hwnd_val as id;
    unsafe {
        let style: usize = msg_send![ns_win, styleMask];
        let utility = 1 << 4; // NSWindowStyleMaskUtilityWindow
        let new_style = if enable { style | utility } else { style & !utility };
        let _: () = msg_send![ns_win, setStyleMask: new_style];
        let ns_app: id = msg_send![class!(NSApplication), sharedApplication];
        let policy = if enable { 1_isize } else { 0_isize };
        let _: () = msg_send![ns_app, setActivationPolicy: policy];
    }
    Ok(())
}

#[pyfunction]
pub fn make_frameless(hwnd_val: usize) -> PyResult<()> {
    let ns_win = hwnd_val as id;
    unsafe {
        let _: () = msg_send![ns_win, setStyleMask: 32783_usize];
        let _: () = msg_send![ns_win, setTitlebarAppearsTransparent: 1_i8];
        let _: () = msg_send![ns_win, setTitleVisibility: 1_isize];
    }
    Ok(())
}

#[pyfunction]
pub fn minimize(hwnd_val: usize) -> PyResult<()> {
    let ns_win = hwnd_val as id;
    unsafe { let _: () = msg_send![ns_win, miniaturize: nil]; }
    Ok(())
}

#[pyfunction]
pub fn set_bounds(hwnd_val: usize, x: i32, y: i32, width: i32, height: i32) -> PyResult<()> {
    let ns_win = hwnd_val as id;
    // NSRect = {NSPoint, NSSize}; using raw [f64; 4] representation
    let frame: [f64; 4] = [x as f64, y as f64, width as f64, height as f64];
    unsafe {
        let _: () = msg_send![ns_win, setFrame: frame display: 1_i8];
    }
    Ok(())
}

#[pyfunction]
pub fn close(hwnd_val: usize) -> PyResult<()> {
    let ns_win = hwnd_val as id;
    unsafe { let _: () = msg_send![ns_win, performClose: nil]; }
    Ok(())
}

#[pyfunction]
pub fn toggle_maximize(hwnd_val: usize) -> PyResult<bool> {
    let ns_win = hwnd_val as id;
    unsafe {
        let zoomed: i8 = msg_send![ns_win, isZoomed];
        let _: () = msg_send![ns_win, zoom: nil];
        Ok(zoomed == 0) // returns true if we just maximised
    }
}

#[pyfunction]
pub fn set_always_on_top(hwnd_val: usize, enable: bool) -> PyResult<()> {
    let ns_win = hwnd_val as id;
    // NSFloatingWindowLevel = 5, NSNormalWindowLevel = 0
    let level: isize = if enable { 5 } else { 0 };
    unsafe { let _: () = msg_send![ns_win, setLevel: level]; }
    Ok(())
}

#[pyfunction]
pub fn start_drag(hwnd_val: usize) -> PyResult<()> {
    // macOS: performWindowDragWithEvent: — but we don't have the event here.
    // Best effort: delegate drag to the window server by calling makeKeyAndOrderFront:
    // Real drag support requires the caller to intercept mouseDown and call this from there.
    let ns_win = hwnd_val as id;
    unsafe { let _: () = msg_send![ns_win, makeKeyAndOrderFront: nil]; }
    Ok(())
}

#[pyfunction]
pub fn hide(hwnd_val: usize) -> PyResult<()> {
    let ns_win = hwnd_val as id;
    unsafe { let _: () = msg_send![ns_win, orderOut: nil]; }
    Ok(())
}

#[pyfunction]
pub fn is_visible(hwnd_val: usize) -> PyResult<bool> {
    let ns_win = hwnd_val as id;
    let visible: i8 = unsafe { msg_send![ns_win, isVisible] };
    Ok(visible != 0)
}

#[pyfunction]
pub fn show(hwnd_val: usize) -> PyResult<()> {
    let ns_win = hwnd_val as id;
    unsafe { let _: () = msg_send![ns_win, makeKeyAndOrderFront: nil]; }
    Ok(())
}

#[pyfunction]
pub fn center(hwnd_val: usize) -> PyResult<()> {
    let ns_win = hwnd_val as id;
    unsafe { let _: () = msg_send![ns_win, center]; }
    Ok(())
}

#[pyfunction]
pub fn set_border_color(_hwnd_val: usize, _color_ref: u32) -> PyResult<()> {
    // macOS has no direct window border colour API — no-op
    Ok(())
}

#[pyfunction]
pub fn set_window_icon(_hwnd_val: usize, icon_path: String) -> PyResult<()> {
    unsafe {
        let path_ns = nsstring(&icon_path);
        let image: id = msg_send![class!(NSImage), alloc];
        let image: id = msg_send![image, initWithContentsOfFile: path_ns];
        if !image.is_null() {
            let ns_app: id = msg_send![class!(NSApplication), sharedApplication];
            let _: () = msg_send![ns_app, setApplicationIconImage: image];
        }
    }
    Ok(())
}

#[pyfunction]
pub fn set_fullscreen(hwnd_val: usize, enable: bool) -> PyResult<()> {
    let ns_win = hwnd_val as id;
    unsafe {
        let style: usize = msg_send![ns_win, styleMask];
        let is_fullscreen = (style & (1 << 14)) != 0; // NSWindowStyleMaskFullScreen
        if enable != is_fullscreen {
            let _: () = msg_send![ns_win, toggleFullScreen: nil];
        }
    }
    Ok(())
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, message, icon_path=None))]
pub fn show_notification(hwnd_val: usize, title: String, message: String, icon_path: Option<String>) -> PyResult<()> {
    let _ = hwnd_val;
    let _ = icon_path;
    unsafe {
        let center: id = msg_send![class!(NSUserNotificationCenter), defaultUserNotificationCenter];
        let notif: id = msg_send![class!(NSUserNotification), new];
        let title_ns = nsstring(&title);
        let body_ns  = nsstring(&message);
        let _: () = msg_send![notif, setTitle: title_ns];
        let _: () = msg_send![notif, setInformativeText: body_ns];
        let _: () = msg_send![center, deliverNotification: notif];
    }
    Ok(())
}

/// macOS NSDockTile does not expose a linear progress bar — we use badge label instead.
#[pyfunction]
pub fn set_taskbar_progress(_hwnd_val: usize, state: String, value: u64, max_value: u64) -> PyResult<()> {
    unsafe {
        let ns_app: id = msg_send![class!(NSApplication), sharedApplication];
        let dock_tile: id = msg_send![ns_app, dockTile];
        let badge = if state == "none" || max_value == 0 {
            nsstring("")
        } else {
            let pct = value * 100 / max_value;
            nsstring(&format!("{}%", pct))
        };
        let _: () = msg_send![dock_tile, setBadgeLabel: badge];
        let _: () = msg_send![dock_tile, display];
    }
    Ok(())
}

/// NSBundle identifier is read-only at runtime — no-op on macOS.
#[pyfunction]
pub fn set_app_id(_app_id: String) -> PyResult<()> {
    Ok(())
}

#[pyfunction]
pub fn set_launch_on_boot(app_name: String, exe_path: String, enable: bool) -> PyResult<bool> {
    use std::{fs, path::PathBuf};
    let home = std::env::var("HOME").map(PathBuf::from)
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("No HOME"))?;
    let agents = home.join("Library/LaunchAgents");
    let plist  = agents.join(format!("com.{}.startup.plist", app_name.to_lowercase()));
    if enable {
        let _ = fs::create_dir_all(&agents);
        let args: Vec<&str> = if exe_path.starts_with('"') && exe_path.ends_with('"') {
            vec![&exe_path[1..exe_path.len() - 1]]
        } else {
            exe_path.split_whitespace().collect()
        };
        let items = args.iter().map(|a| format!("        <string>{}</string>", a)).collect::<Vec<_>>().join("\n");
        let xml = format!(
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\">\n<dict>\n    <key>Label</key>\n    <string>com.{}.startup</string>\n    <key>ProgramArguments</key>\n    <array>\n{}\n    </array>\n    <key>RunAtLoad</key>\n    <true/>\n</dict>\n</plist>",
            app_name.to_lowercase(), items
        );
        fs::write(plist, xml).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    } else if plist.exists() {
        let _ = fs::remove_file(plist);
    }
    Ok(true)
}
