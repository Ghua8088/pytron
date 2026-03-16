use pyo3::prelude::*;
use windows::Win32::Foundation::{HWND, WPARAM, LPARAM};
use windows::Win32::UI::WindowsAndMessaging::{
    GetMessageW, TranslateMessage, DispatchMessageW, PostMessageW, SetForegroundWindow,
    LoadImageW, IMAGE_ICON, LR_LOADFROMFILE,
    MSG,
};
use windows::Win32::UI::Shell::{
    Shell_NotifyIconW, NOTIFYICONDATAW, NIM_ADD, NIM_DELETE, NIF_ICON, NIF_MESSAGE, NIF_TIP,
};

// ─── Hidden message-only window ──────────────────────────────────────────────

unsafe extern "system" fn tray_wnd_proc(
    hwnd: HWND,
    msg: u32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> windows::Win32::Foundation::LRESULT {
    unsafe { windows::Win32::UI::WindowsAndMessaging::DefWindowProcW(hwnd, msg, wparam, lparam) }
}

/// Create a hidden message-only window for tray notifications. Returns HWND as usize.
#[pyfunction]
pub fn tray_create_window(class_name: String, title: String) -> PyResult<usize> {
    use windows::Win32::System::LibraryLoader::GetModuleHandleW;
    use windows::Win32::Foundation::HINSTANCE;
    use windows::Win32::UI::WindowsAndMessaging::{
        WNDCLASSW, RegisterClassW, CreateWindowExW, WINDOW_EX_STYLE, WINDOW_STYLE,
        HWND_MESSAGE,
    };
    use windows::core::PCWSTR;

    let class_w: Vec<u16> = class_name.encode_utf16().chain(std::iter::once(0)).collect();
    let title_w: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();

    unsafe {
        let h_module = GetModuleHandleW(PCWSTR::null())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        let h_instance = HINSTANCE(h_module.0);

        let wc = WNDCLASSW {
            lpfnWndProc: Some(tray_wnd_proc),
            hInstance: h_instance,
            lpszClassName: PCWSTR(class_w.as_ptr()),
            ..Default::default()
        };
        RegisterClassW(&wc); // ignore error if already registered

        // HWND_MESSAGE creates a message-only window — invisible, no z-order,
        // not enumerable. This is the only reliable way to receive Shell_NotifyIcon
        // callback messages on modern Windows. Using NULL/HWND::default() as parent
        // creates a regular hidden top-level window which can miss shell notifications.
        let hwnd = CreateWindowExW(
            WINDOW_EX_STYLE::default(),
            PCWSTR(class_w.as_ptr()),
            PCWSTR(title_w.as_ptr()),
            WINDOW_STYLE::default(),
            0, 0, 0, 0,
            HWND_MESSAGE,
            windows::Win32::UI::WindowsAndMessaging::HMENU::default(),
            h_instance,
            None,
        );
        if hwnd.0 == 0 {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("CreateWindowExW returned null"));
        }
        Ok(hwnd.0 as usize)
    }
}

/// Blocking GetMessageW returning (hwnd, msg, wparam, lparam).
/// Returns None on WM_QUIT (res==0) or error (res==-1).
/// Returns the i32 result as the 5th tuple element so Python can distinguish  
/// WM_QUIT (0) from a GetMessageW error (-1).
#[pyfunction]
pub fn tray_get_message_ex(py: Python<'_>) -> PyResult<Option<(usize, u32, usize, isize, i32)>> {
    let (res, hwnd_val, message, wparam, lparam) = py.allow_threads(|| unsafe {
        let mut msg = MSG::default();
        let res = GetMessageW(&mut msg, HWND::default(), 0, 0);
        (res.0, msg.hwnd.0 as usize, msg.message, msg.wParam.0, msg.lParam.0)
    });
    if res > 0 {
        Ok(Some((hwnd_val, message, wparam, lparam, res)))
    } else {
        // res == 0  → WM_QUIT
        // res == -1 → GetMessageW error (invalid HWND, etc.)
        Ok(Some((0, 0xFFFF_FFFF, 0, 0, res)))  // sentinel so Python can log the reason
    }
}

/// TranslateMessage + DispatchMessageW for a message from tray_get_message_ex.
#[pyfunction]
pub fn tray_translate_dispatch(hwnd_val: usize, msg: u32, wparam: usize, lparam: isize) -> PyResult<()> {
    unsafe {
        let m = MSG { hwnd: HWND(hwnd_val as isize), message: msg, wParam: WPARAM(wparam), lParam: LPARAM(lparam), ..Default::default() };
        let _ = TranslateMessage(&m);
        DispatchMessageW(&m);
    }
    Ok(())
}

// ─── Tray icon lifecycle ─────────────────────────────────────────────────────

/// Add (NIM_ADD) a system-tray icon. callback_msg is typically WM_USER+1.
#[pyfunction]
pub fn tray_add_icon(hwnd_val: usize, hicon_val: usize, id: u32, tip: String, callback_msg: u32) -> PyResult<bool> {
    use windows::Win32::UI::WindowsAndMessaging::HICON;
    let hwnd  = HWND(hwnd_val as isize);
    let hicon = HICON(hicon_val as isize);
    unsafe {
        let mut nid = NOTIFYICONDATAW::default();
        nid.cbSize = std::mem::size_of::<NOTIFYICONDATAW>() as u32;
        nid.hWnd = hwnd;
        nid.uID  = id;
        nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
        nid.uCallbackMessage = callback_msg;
        nid.hIcon = hicon;
        let tip_u16: Vec<u16> = tip.encode_utf16().collect();
        let len = tip_u16.len().min(127);
        nid.szTip[..len].copy_from_slice(&tip_u16[..len]);
        Ok(Shell_NotifyIconW(NIM_ADD, &nid).as_bool())
    }
}

/// Remove (NIM_DELETE) a system-tray icon.
#[pyfunction]
pub fn tray_remove_icon(hwnd_val: usize, id: u32) -> PyResult<()> {
    let hwnd = HWND(hwnd_val as isize);
    unsafe {
        let mut nid = NOTIFYICONDATAW::default();
        nid.cbSize = std::mem::size_of::<NOTIFYICONDATAW>() as u32;
        nid.hWnd = hwnd;
        nid.uID  = id;
        let _ = Shell_NotifyIconW(NIM_DELETE, &nid);
    }
    Ok(())
}

/// Destroy a window created by tray_create_window.
#[pyfunction]
pub fn tray_destroy_window(hwnd_val: usize) -> PyResult<()> {
    use windows::Win32::UI::WindowsAndMessaging::DestroyWindow;
    unsafe { let _ = DestroyWindow(HWND(hwnd_val as isize)); }
    Ok(())
}

/// Post any message to a window (e.g. to wake / close the message loop).
#[pyfunction]
pub fn tray_post_message(hwnd_val: usize, msg: u32, wparam: usize, lparam: isize) -> PyResult<()> {
    unsafe { let _ = PostMessageW(HWND(hwnd_val as isize), msg, WPARAM(wparam), LPARAM(lparam)); }
    Ok(())
}

// ─── Icon loading ────────────────────────────────────────────────────────────

/// Load an icon from file. Returns HICON as usize.
#[pyfunction]
pub fn tray_load_icon(path: String, w: i32, h: i32) -> PyResult<usize> {
    let path_u16: Vec<u16> = path.encode_utf16().chain(std::iter::once(0)).collect();
    unsafe {
        let handle = LoadImageW(None, windows::core::PCWSTR(path_u16.as_ptr()), IMAGE_ICON, w, h, LR_LOADFROMFILE)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(handle.0 as usize)
    }
}

/// Load the default application icon (IDI_APPLICATION). Returns HICON as usize.
#[pyfunction]
pub fn tray_load_default_icon() -> PyResult<usize> {
    use windows::Win32::UI::WindowsAndMessaging::{LoadIconW, IDI_APPLICATION};
    unsafe {
        let h = LoadIconW(None, IDI_APPLICATION)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(h.0 as usize)
    }
}

/// Destroy an icon handle returned by tray_load_icon / tray_load_default_icon.
#[pyfunction]
pub fn tray_destroy_icon(hicon_val: usize) -> PyResult<()> {
    use windows::Win32::UI::WindowsAndMessaging::{DestroyIcon, HICON};
    unsafe { let _ = DestroyIcon(HICON(hicon_val as isize)); }
    Ok(())
}

// ─── Context menu ────────────────────────────────────────────────────────────

/// Create a pop-up menu. Returns HMENU as usize.
#[pyfunction]
pub fn tray_create_popup_menu() -> PyResult<usize> {
    use windows::Win32::UI::WindowsAndMessaging::CreatePopupMenu;
    unsafe {
        let hmenu = CreatePopupMenu()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(hmenu.0 as usize)
    }
}

/// Append a string item to a menu. flags=0 → enabled, unchecked (MFT_STRING).
#[pyfunction]
pub fn tray_append_menu_item(hmenu_val: usize, flags: u32, id: u32, label: String) -> PyResult<()> {
    use windows::Win32::UI::WindowsAndMessaging::{AppendMenuW, HMENU, MENU_ITEM_FLAGS};
    let label_u16: Vec<u16> = label.encode_utf16().chain(std::iter::once(0)).collect();
    unsafe {
        let _ = AppendMenuW(HMENU(hmenu_val as isize), MENU_ITEM_FLAGS(flags), id as usize, windows::core::PCWSTR(label_u16.as_ptr()));
    }
    Ok(())
}

/// Append a separator to a menu.
#[pyfunction]
pub fn tray_append_separator(hmenu_val: usize) -> PyResult<()> {
    use windows::Win32::UI::WindowsAndMessaging::{AppendMenuW, HMENU, MF_SEPARATOR};
    unsafe {
        let _ = AppendMenuW(HMENU(hmenu_val as isize), MF_SEPARATOR, 0, windows::core::PCWSTR::null());
    }
    Ok(())
}

/// Show a pop-up menu using TPM_RETURNCMD — returns the selected item ID, or 0 if dismissed.
/// Automatically destroys the menu handle after tracking.
#[pyfunction]
pub fn tray_track_popup_menu(py: Python<'_>, hmenu_val: usize, flags: u32, x: i32, y: i32, hwnd_val: usize) -> PyResult<u32> {
    use windows::Win32::UI::WindowsAndMessaging::{TrackPopupMenu, DestroyMenu, HMENU, TRACK_POPUP_MENU_FLAGS, TPM_RETURNCMD};
    let hwnd  = HWND(hwnd_val as isize);
    let hmenu = HMENU(hmenu_val as isize);
    let selected = py.allow_threads(|| unsafe {
        let _ = SetForegroundWindow(hwnd);
        // TPM_RETURNCMD makes TrackPopupMenu return the item ID directly instead
        // of posting WM_COMMAND, so we never need to fish it out of GetMessageW.
        let id = TrackPopupMenu(
            hmenu,
            TRACK_POPUP_MENU_FLAGS(flags) | TPM_RETURNCMD,
            x, y, 0, hwnd, None,
        );
        let _ = PostMessageW(hwnd, 0, WPARAM(0), LPARAM(0)); // WM_NULL flush
        let _ = DestroyMenu(hmenu);
        id.0 as u32
    });
    Ok(selected)
}

/// Return the current cursor screen position as (x, y).
#[pyfunction]
pub fn tray_get_cursor_pos() -> PyResult<(i32, i32)> {
    use windows::Win32::Foundation::POINT;
    use windows::Win32::UI::WindowsAndMessaging::GetCursorPos;
    unsafe {
        let mut pt = POINT::default();
        let _ = GetCursorPos(&mut pt);
        Ok((pt.x, pt.y))
    }
}

// ─── v2 tray API — backed by the tray-icon crate (Tauri team) ───────────────
//
// Replaces all the raw Shell_NotifyIconW / HWND / TrackPopupMenu plumbing.
// tray-icon handles the message-only window, NIM_SETVERSION, menu popup, etc.
// Python calls: tray_v2_create → loop { tray_v2_poll_event } → tray_v2_destroy

use std::cell::RefCell;
use tray_icon::{TrayIcon, TrayIconBuilder, TrayIconEvent, MouseButton, MouseButtonState};
use tray_icon::menu::{Menu, MenuItem, MenuEvent, PredefinedMenuItem};

thread_local! {
    static TRAY_V2: RefCell<Option<TrayIcon>> = RefCell::new(None);
    /// Thread ID of the thread that called tray_v2_create — used by tray_v2_interrupt
    /// to post WM_QUIT and unblock the blocking GetMessageW in tray_v2_poll_event.
    static TRAY_V2_TID: RefCell<u32> = RefCell::new(0);
}

fn load_tray_icon_v2(path: Option<String>) -> tray_icon::Icon {
    if let Some(ref p) = path {
        if let Ok(img) = image::open(p) {
            let rgba = img.into_rgba8();
            let (w, h) = (rgba.width(), rgba.height());
            if let Ok(icon) = tray_icon::Icon::from_rgba(rgba.into_raw(), w, h) {
                return icon;
            }
        }
    }
    // Fallback: 32×32 solid blue square
    let rgba: Vec<u8> = (0..32u32 * 32u32).flat_map(|_| [0u8, 122, 204, 255]).collect();
    tray_icon::Icon::from_rgba(rgba, 32, 32).expect("fallback icon")
}

/// Create a tray icon with an attached context menu via the tray-icon crate.
/// `items` is a list of (id, label, is_separator).  The id is returned verbatim
/// in tray_v2_poll_event menu events so Python can dispatch to the right callback.
/// The crate automatically shows the menu on right-click.
#[pyfunction]
#[pyo3(signature = (tooltip, items, icon_path=None))]
pub fn tray_v2_create(tooltip: String, items: Vec<(String, String, bool)>, icon_path: Option<String>) -> PyResult<()> {
    let icon = load_tray_icon_v2(icon_path);

    let menu = Menu::new();
    for (id, label, is_sep) in &items {
        if *is_sep {
            let _ = menu.append(&PredefinedMenuItem::separator());
        } else {
            let item = MenuItem::with_id(id.as_str(), label, true, None);
            let _ = menu.append(&item);
        }
    }

    let tray = TrayIconBuilder::new()
        .with_icon(icon)
        .with_tooltip(&tooltip)
        .with_menu(Box::new(menu))
        .with_menu_on_left_click(false)  // left-click → Click event (show app); right-click → menu
        .build()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    // Record the calling thread ID so tray_v2_interrupt can wake us later.
    use windows::Win32::System::Threading::GetCurrentThreadId;
    TRAY_V2_TID.with(|t| *t.borrow_mut() = unsafe { GetCurrentThreadId() });
    TRAY_V2.with(|t| *t.borrow_mut() = Some(tray));
    Ok(())
}

/// Poll tray/menu events. Uses blocking GetMessageW — zero CPU, instant response.
/// Blocks until a Win32 message arrives, dispatches it so tray-icon's WndProc
/// fires, then checks the event channels.
/// Returns None only when WM_QUIT is received (posted by tray_v2_interrupt on
/// shutdown). Python should break its loop on None.
#[pyfunction]
pub fn tray_v2_poll_event(py: Python<'_>) -> PyResult<Option<(String, String)>> {
    py.allow_threads(|| {
        let t_recv = TrayIconEvent::receiver();
        let m_recv = MenuEvent::receiver();

        loop {
            let mut msg = MSG::default();
            // Blocks the OS thread until a message arrives.
            // Returns FALSE when the message is WM_QUIT — our shutdown signal.
            let got = unsafe { GetMessageW(&mut msg, None, 0, 0) };
            if !got.as_bool() {
                return Ok(None); // WM_QUIT → tell Python to stop
            }

            unsafe {
                let _ = TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }

            // Check if tray-icon's WndProc deposited an event into its channels.
            if let Ok(event) = t_recv.try_recv() {
                let kind = match &event {
                    TrayIconEvent::Click { button, button_state, .. } => {
                        match (button, button_state) {
                            (MouseButton::Left, MouseButtonState::Up) => "left_click",
                            (MouseButton::Right, MouseButtonState::Up) => "right_click",
                            _ => "unknown",
                        }
                    },
                    TrayIconEvent::DoubleClick { .. } => "double_click",
                    _ => "unknown",
                };
                return Ok(Some((kind.to_string(), String::new())));
            }

            if let Ok(event) = m_recv.try_recv() {
                return Ok(Some(("menu".to_string(), event.id.0.clone())));
            }

            // Unrelated Win32 message dispatched (e.g. internal WM_TIMER);
            // loop back and block on the next one.
        }
    })
}

/// Unblock tray_v2_poll_event from any thread by posting WM_QUIT to the tray
/// thread. GetMessageW returns FALSE, poll_event returns None, Python breaks.
#[pyfunction]
pub fn tray_v2_interrupt() -> PyResult<()> {
    use windows::Win32::UI::WindowsAndMessaging::{PostThreadMessageW, WM_QUIT};
    let tid = TRAY_V2_TID.with(|t| *t.borrow());
    if tid != 0 {
        unsafe {
            let _ = PostThreadMessageW(tid, WM_QUIT, WPARAM(0), LPARAM(0));
        }
    }
    Ok(())
}

/// Destroy the tray icon (drops the TrayIcon, which calls NIM_DELETE internally).
#[pyfunction]
pub fn tray_v2_destroy() -> PyResult<()> {
    TRAY_V2.with(|t| *t.borrow_mut() = None);
    Ok(())
}
