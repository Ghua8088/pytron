use pyo3::prelude::*;
use windows::Win32::Foundation::{HWND, RECT, WPARAM, LPARAM, HANDLE};
use windows::Win32::UI::WindowsAndMessaging::{
    GetWindowLongW, SetWindowLongW, SetWindowPos, GWL_EXSTYLE, GWL_STYLE,
    WS_EX_TOOLWINDOW, WS_EX_APPWINDOW, SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER, SWP_FRAMECHANGED,
    WS_CAPTION, WS_THICKFRAME, SWP_NOACTIVATE, SW_MINIMIZE, SW_MAXIMIZE, SW_RESTORE, SW_HIDE, SW_SHOW,
    ShowWindow, IsZoomed, PostMessageW, SendMessageW, IsWindowVisible, SetForegroundWindow,
    GetWindowRect, GetSystemMetrics, WM_CLOSE, WM_NCLBUTTONDOWN, HTCAPTION,
    SM_CXSCREEN, SM_CYSCREEN, HWND_TOPMOST, HWND_NOTOPMOST, WM_SETICON, ICON_SMALL, ICON_BIG,
};
use windows::Win32::UI::Input::KeyboardAndMouse::ReleaseCapture;
use windows::Win32::Graphics::Gdi::{GetMonitorInfoW, MONITORINFO, MonitorFromWindow, MONITOR_DEFAULTTOPRIMARY};
use windows::Win32::Graphics::Dwm::{DwmSetWindowAttribute, DWMWA_BORDER_COLOR};
use windows::Win32::UI::WindowsAndMessaging::{LoadImageW, IMAGE_ICON, LR_LOADFROMFILE, LR_DEFAULTSIZE};
use windows::Win32::System::Com::{CoCreateInstance, CoInitialize, CLSCTX_INPROC_SERVER};
use windows::Win32::UI::Shell::{
    ITaskbarList3, TaskbarList,
    Shell_NotifyIconW, NOTIFYICONDATAW, NIM_ADD, NIM_MODIFY, NIM_SETVERSION,
    NIF_ICON, NIF_MESSAGE, NIF_TIP, NIF_INFO, NOTIFYICON_VERSION_4,
    SetCurrentProcessExplicitAppUserModelID, NIIF_INFO,
};
use dashmap::DashMap;
use once_cell::sync::Lazy;

// ─── Fullscreen state ────────────────────────────────────────────────────────

struct FullscreenState {
    style: u32,
    rect: RECT,
}

static FULLSCREEN_STORAGE: Lazy<DashMap<usize, FullscreenState>> = Lazy::new(DashMap::new);

// ─── Window management ───────────────────────────────────────────────────────

#[pyfunction]
pub fn set_utility_window(hwnd_val: usize, enable: bool) -> PyResult<()> {
    let hwnd = HWND(hwnd_val as isize);
    unsafe {
        let mut ex_style = GetWindowLongW(hwnd, GWL_EXSTYLE);
        if enable {
            ex_style = (ex_style | WS_EX_TOOLWINDOW.0 as i32) & !(WS_EX_APPWINDOW.0 as i32);
        } else {
            ex_style = (ex_style | WS_EX_APPWINDOW.0 as i32) & !(WS_EX_TOOLWINDOW.0 as i32);
        }
        SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style);
        let _ = SetWindowPos(hwnd, HWND::default(), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED | SWP_NOACTIVATE);

        let _ = CoInitialize(None);
        if let Ok(taskbar) = CoCreateInstance::<_, ITaskbarList3>(&TaskbarList, None, CLSCTX_INPROC_SERVER) {
            if let Ok(_) = taskbar.HrInit() {
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
pub fn set_taskbar_progress(hwnd_val: usize, state: String, value: u64, max_value: u64) -> PyResult<()> {
    let hwnd = HWND(hwnd_val as isize);
    unsafe {
        let _ = CoInitialize(None);
        if let Ok(taskbar) = CoCreateInstance::<_, ITaskbarList3>(&TaskbarList, None, CLSCTX_INPROC_SERVER) {
            if let Ok(_) = taskbar.HrInit() {
                let flags = match state.as_str() {
                    "indeterminate" => 1,
                    "normal"        => 2,
                    "error"         => 4,
                    "paused"        => 8,
                    _               => 0,
                };
                let _ = taskbar.SetProgressState(hwnd, windows::Win32::UI::Shell::TBPFLAG(flags));
                if flags != 0 && flags != 1 {
                    let _ = taskbar.SetProgressValue(hwnd, value, max_value);
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
        SetWindowLongW(hwnd, GWL_STYLE, style & !(WS_CAPTION.0 as i32));
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
        if IsZoomed(hwnd).as_bool() {
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
            let width  = rect.right  - rect.left;
            let height = rect.bottom - rect.top;
            let x = (GetSystemMetrics(SM_CXSCREEN) - width)  / 2;
            let y = (GetSystemMetrics(SM_CYSCREEN) - height) / 2;
            let _ = SetWindowPos(hwnd, HWND::default(), x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER);
        }
    }
    Ok(())
}

#[pyfunction]
pub fn set_border_color(hwnd_val: usize, color_ref: u32) -> PyResult<()> {
    let hwnd = HWND(hwnd_val as isize);
    unsafe {
        let _ = DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR, &color_ref as *const u32 as *const _, 4);
    }
    Ok(())
}

#[pyfunction]
pub fn set_window_icon(hwnd_val: usize, icon_path: String) -> PyResult<()> {
    let hwnd = HWND(hwnd_val as isize);
    let path_u16: Vec<u16> = icon_path.encode_utf16().chain(std::iter::once(0)).collect();
    unsafe {
        if let Ok(h) = LoadImageW(None, windows::core::PCWSTR(path_u16.as_ptr()), IMAGE_ICON, 16, 16, LR_LOADFROMFILE | LR_DEFAULTSIZE) {
            SendMessageW(hwnd, WM_SETICON, WPARAM(ICON_SMALL as usize), LPARAM(h.0));
        }
        if let Ok(h) = LoadImageW(None, windows::core::PCWSTR(path_u16.as_ptr()), IMAGE_ICON, 32, 32, LR_LOADFROMFILE | LR_DEFAULTSIZE) {
            SendMessageW(hwnd, WM_SETICON, WPARAM(ICON_BIG as usize), LPARAM(h.0));
        }
    }
    Ok(())
}

#[pyfunction]
pub fn set_fullscreen(hwnd_val: usize, enable: bool) -> PyResult<()> {
    let hwnd = HWND(hwnd_val as isize);
    unsafe {
        if enable {
            if FULLSCREEN_STORAGE.contains_key(&hwnd_val) {
                return Ok(());
            }
            let mut rect = RECT::default();
            let _ = GetWindowRect(hwnd, &mut rect);
            let style = GetWindowLongW(hwnd, GWL_STYLE) as u32;
            FULLSCREEN_STORAGE.insert(hwnd_val, FullscreenState { style, rect });

            let new_style = style & !(WS_CAPTION.0 | WS_THICKFRAME.0);
            let _ = SetWindowLongW(hwnd, GWL_STYLE, new_style as i32);

            let monitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTOPRIMARY);
            let mut info = MONITORINFO { cbSize: std::mem::size_of::<MONITORINFO>() as u32, ..Default::default() };
            let _ = GetMonitorInfoW(monitor, &mut info);
            let rc = info.rcMonitor;
            let _ = SetWindowPos(hwnd, HWND::default(), rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top, SWP_NOZORDER | SWP_FRAMECHANGED);
        } else if let Some((_, saved)) = FULLSCREEN_STORAGE.remove(&hwnd_val) {
            let _ = SetWindowLongW(hwnd, GWL_STYLE, saved.style as i32);
            let r = saved.rect;
            let _ = SetWindowPos(hwnd, HWND::default(), r.left, r.top, r.right - r.left, r.bottom - r.top, SWP_NOZORDER | SWP_FRAMECHANGED);
        }
    }
    Ok(())
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, message, icon_path=None))]
pub fn show_notification(hwnd_val: usize, title: String, message: String, icon_path: Option<String>) -> PyResult<()> {
    let hwnd = HWND(hwnd_val as isize);
    unsafe {
        let mut nid = NOTIFYICONDATAW::default();
        nid.cbSize = std::mem::size_of::<NOTIFYICONDATAW>() as u32;
        nid.hWnd  = hwnd;
        nid.uID   = 2000;

        let mut h_icon = HANDLE::default();
        if let Some(path) = icon_path {
            let path_u16: Vec<u16> = path.encode_utf16().chain(std::iter::once(0)).collect();
            if let Ok(h) = LoadImageW(None, windows::core::PCWSTR(path_u16.as_ptr()), IMAGE_ICON, 16, 16, LR_LOADFROMFILE) {
                h_icon = HANDLE(h.0);
            }
        }
        nid.hIcon  = windows::Win32::UI::WindowsAndMessaging::HICON(h_icon.0);
        nid.uFlags = NIF_ICON | NIF_TIP | NIF_MESSAGE;

        let title_u16: Vec<u16> = title.encode_utf16().collect();
        let len = title_u16.len().min(127);
        nid.szTip[..len].copy_from_slice(&title_u16[..len]);

        let _ = Shell_NotifyIconW(NIM_ADD, &nid);
        nid.Anonymous.uVersion = NOTIFYICON_VERSION_4;
        let _ = Shell_NotifyIconW(NIM_SETVERSION, &nid);

        nid.uFlags = NIF_INFO | NIF_ICON | NIF_TIP;

        let msg_u16: Vec<u16> = message.encode_utf16().collect();
        let m_len = msg_u16.len().min(255);
        nid.szInfo[..m_len].copy_from_slice(&msg_u16[..m_len]);

        let t_len = title_u16.len().min(63);
        nid.szInfoTitle[..t_len].copy_from_slice(&title_u16[..t_len]);

        nid.dwInfoFlags = NIIF_INFO;
        let _ = Shell_NotifyIconW(NIM_MODIFY, &nid);
    }
    Ok(())
}

#[pyfunction]
pub fn set_app_id(app_id: String) -> PyResult<()> {
    let app_id_u16: Vec<u16> = app_id.encode_utf16().chain(std::iter::once(0)).collect();
    unsafe {
        let _ = SetCurrentProcessExplicitAppUserModelID(windows::core::PCWSTR(app_id_u16.as_ptr()));
    }
    Ok(())
}

// ─── Registry / boot ─────────────────────────────────────────────────────────

#[pyfunction]
pub fn set_launch_on_boot(app_name: String, exe_path: String, enable: bool) -> PyResult<bool> {
    use windows::Win32::System::Registry::{
        RegCloseKey, RegCreateKeyExW, RegDeleteValueW, RegSetValueExW,
        HKEY_CURRENT_USER, KEY_SET_VALUE, REG_SZ, REG_OPTION_NON_VOLATILE,
    };
    use windows::core::PCWSTR;

    let sub_key = "Software\\Microsoft\\Windows\\CurrentVersion\\Run\0";
    let sub_key_u16: Vec<u16>  = sub_key.encode_utf16().collect();
    let app_name_u16: Vec<u16> = format!("{}\0", app_name).encode_utf16().collect();

    unsafe {
        let mut hkey = windows::Win32::System::Registry::HKEY::default();
        if RegCreateKeyExW(HKEY_CURRENT_USER, PCWSTR(sub_key_u16.as_ptr()), 0, PCWSTR::null(), REG_OPTION_NON_VOLATILE, KEY_SET_VALUE, None, &mut hkey, None).is_ok() {
            if enable {
                let exe_u16: Vec<u16> = format!("{}\0", exe_path).encode_utf16().collect();
                let _ = RegSetValueExW(hkey, PCWSTR(app_name_u16.as_ptr()), 0, REG_SZ,
                    Some(std::slice::from_raw_parts(exe_u16.as_ptr() as *const u8, exe_u16.len() * 2)));
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
