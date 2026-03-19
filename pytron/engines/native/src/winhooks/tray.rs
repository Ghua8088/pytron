use pyo3::prelude::*;
use std::cell::RefCell;
use tray_icon::menu::{Menu, MenuEvent, MenuItem, PredefinedMenuItem};
use tray_icon::{MouseButton, MouseButtonState, TrayIcon, TrayIconBuilder, TrayIconEvent};
use windows::Win32::Foundation::{HWND, LPARAM, WPARAM};
use windows::Win32::UI::Shell::{
    NIF_ICON, NIF_MESSAGE, NIF_TIP, NIM_ADD, NIM_DELETE, NOTIFYICONDATAW, Shell_NotifyIconW,
};
use windows::Win32::UI::WindowsAndMessaging::{
    DispatchMessageW, GetMessageW, IMAGE_ICON, LR_LOADFROMFILE, LoadImageW, MSG, PostMessageW,
    SetForegroundWindow, TranslateMessage,
};

unsafe extern "system" fn tray_wnd_proc(
    hwnd: HWND,
    msg: u32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> windows::Win32::Foundation::LRESULT {
    unsafe { windows::Win32::UI::WindowsAndMessaging::DefWindowProcW(hwnd, msg, wparam, lparam) }
}

#[pyfunction]
pub fn tray_create_window(class_name: String, title: String) -> PyResult<usize> {
    use windows::Win32::Foundation::HINSTANCE;
    use windows::Win32::System::LibraryLoader::GetModuleHandleW;
    use windows::Win32::UI::WindowsAndMessaging::{
        CreateWindowExW, HMENU, HWND_MESSAGE, RegisterClassW, WINDOW_EX_STYLE, WINDOW_STYLE,
        WNDCLASSW,
    };

    let class_w: Vec<u16> = class_name.encode_utf16().chain(std::iter::once(0)).collect();
    let title_w: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();

    unsafe {
        let h_module = GetModuleHandleW(windows::core::PCWSTR::null())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        let h_instance = HINSTANCE(h_module.0);

        let wc = WNDCLASSW {
            lpfnWndProc: Some(tray_wnd_proc),
            hInstance: h_instance,
            lpszClassName: windows::core::PCWSTR(class_w.as_ptr()),
            ..Default::default()
        };
        RegisterClassW(&wc);

        let hwnd = CreateWindowExW(
            WINDOW_EX_STYLE::default(),
            windows::core::PCWSTR(class_w.as_ptr()),
            windows::core::PCWSTR(title_w.as_ptr()),
            WINDOW_STYLE::default(),
            0,
            0,
            0,
            0,
            HWND_MESSAGE,
            HMENU::default(),
            h_instance,
            None,
        );
        if hwnd.0 == 0 {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                "CreateWindowExW returned null",
            ));
        }
        Ok(hwnd.0 as usize)
    }
}

#[pyfunction]
pub fn tray_get_message_ex(py: Python<'_>) -> PyResult<Option<(usize, u32, usize, isize, i32)>> {
    let (res, hwnd_val, message, wparam, lparam) = py.allow_threads(|| unsafe {
        let mut msg = MSG::default();
        let res = GetMessageW(&mut msg, HWND::default(), 0, 0);
        (
            res.0,
            msg.hwnd.0 as usize,
            msg.message,
            msg.wParam.0,
            msg.lParam.0,
        )
    });
    if res > 0 {
        Ok(Some((hwnd_val, message, wparam, lparam, res)))
    } else {
        Ok(Some((0, 0xFFFF_FFFF, 0, 0, res)))
    }
}

#[pyfunction]
pub fn tray_translate_dispatch(
    hwnd_val: usize,
    msg: u32,
    wparam: usize,
    lparam: isize,
) -> PyResult<()> {
    unsafe {
        let m = MSG {
            hwnd: HWND(hwnd_val as isize),
            message: msg,
            wParam: WPARAM(wparam),
            lParam: LPARAM(lparam),
            ..Default::default()
        };
        let _ = TranslateMessage(&m);
        DispatchMessageW(&m);
    }
    Ok(())
}

#[pyfunction]
pub fn tray_add_icon(
    hwnd_val: usize,
    hicon_val: usize,
    id: u32,
    tip: String,
    callback_msg: u32,
) -> PyResult<bool> {
    use windows::Win32::UI::WindowsAndMessaging::HICON;
    let hwnd = HWND(hwnd_val as isize);
    let hicon = HICON(hicon_val as isize);
    unsafe {
        let mut nid = NOTIFYICONDATAW::default();
        nid.cbSize = std::mem::size_of::<NOTIFYICONDATAW>() as u32;
        nid.hWnd = hwnd;
        nid.uID = id;
        nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
        nid.uCallbackMessage = callback_msg;
        nid.hIcon = hicon;
        let tip_u16: Vec<u16> = tip.encode_utf16().collect();
        let len = tip_u16.len().min(127);
        nid.szTip[..len].copy_from_slice(&tip_u16[..len]);
        Ok(Shell_NotifyIconW(NIM_ADD, &nid).as_bool())
    }
}

#[pyfunction]
pub fn tray_remove_icon(hwnd_val: usize, id: u32) -> PyResult<()> {
    let hwnd = HWND(hwnd_val as isize);
    unsafe {
        let mut nid = NOTIFYICONDATAW::default();
        nid.cbSize = std::mem::size_of::<NOTIFYICONDATAW>() as u32;
        nid.hWnd = hwnd;
        nid.uID = id;
        let _ = Shell_NotifyIconW(NIM_DELETE, &nid);
    }
    Ok(())
}

#[pyfunction]
pub fn tray_destroy_window(hwnd_val: usize) -> PyResult<()> {
    use windows::Win32::UI::WindowsAndMessaging::DestroyWindow;
    unsafe {
        let _ = DestroyWindow(HWND(hwnd_val as isize));
    }
    Ok(())
}

#[pyfunction]
pub fn tray_post_message(hwnd_val: usize, msg: u32, wparam: usize, lparam: isize) -> PyResult<()> {
    unsafe {
        let _ = PostMessageW(HWND(hwnd_val as isize), msg, WPARAM(wparam), LPARAM(lparam));
    }
    Ok(())
}

#[pyfunction]
pub fn tray_load_icon(path: String, w: i32, h: i32) -> PyResult<usize> {
    let path_u16: Vec<u16> = path.encode_utf16().chain(std::iter::once(0)).collect();
    unsafe {
        let handle = LoadImageW(
            None,
            windows::core::PCWSTR(path_u16.as_ptr()),
            IMAGE_ICON,
            w,
            h,
            LR_LOADFROMFILE,
        )
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(handle.0 as usize)
    }
}

#[pyfunction]
pub fn tray_load_default_icon() -> PyResult<usize> {
    use windows::Win32::UI::WindowsAndMessaging::{IDI_APPLICATION, LoadIconW};
    unsafe {
        let h = LoadIconW(None, IDI_APPLICATION)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(h.0 as usize)
    }
}

#[pyfunction]
pub fn tray_destroy_icon(hicon_val: usize) -> PyResult<()> {
    use windows::Win32::UI::WindowsAndMessaging::{DestroyIcon, HICON};
    unsafe {
        let _ = DestroyIcon(HICON(hicon_val as isize));
    }
    Ok(())
}

#[pyfunction]
pub fn tray_create_popup_menu() -> PyResult<usize> {
    use windows::Win32::UI::WindowsAndMessaging::CreatePopupMenu;
    unsafe {
        let hmenu = CreatePopupMenu()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(hmenu.0 as usize)
    }
}

#[pyfunction]
pub fn tray_append_menu_item(hmenu_val: usize, flags: u32, id: u32, label: String) -> PyResult<()> {
    use windows::Win32::UI::WindowsAndMessaging::{AppendMenuW, HMENU, MENU_ITEM_FLAGS};
    let label_u16: Vec<u16> = label.encode_utf16().chain(std::iter::once(0)).collect();
    unsafe {
        let _ = AppendMenuW(
            HMENU(hmenu_val as isize),
            MENU_ITEM_FLAGS(flags),
            id as usize,
            windows::core::PCWSTR(label_u16.as_ptr()),
        );
    }
    Ok(())
}

#[pyfunction]
pub fn tray_append_separator(hmenu_val: usize) -> PyResult<()> {
    use windows::Win32::UI::WindowsAndMessaging::{AppendMenuW, HMENU, MF_SEPARATOR};
    unsafe {
        let _ = AppendMenuW(
            HMENU(hmenu_val as isize),
            MF_SEPARATOR,
            0,
            windows::core::PCWSTR::null(),
        );
    }
    Ok(())
}

#[pyfunction]
pub fn tray_track_popup_menu(
    py: Python<'_>,
    hmenu_val: usize,
    flags: u32,
    x: i32,
    y: i32,
    hwnd_val: usize,
) -> PyResult<u32> {
    use windows::Win32::UI::WindowsAndMessaging::{
        DestroyMenu, HMENU, TPM_RETURNCMD, TRACK_POPUP_MENU_FLAGS, TrackPopupMenu,
    };
    let hwnd = HWND(hwnd_val as isize);
    let hmenu = HMENU(hmenu_val as isize);
    let selected = py.allow_threads(|| unsafe {
        let _ = SetForegroundWindow(hwnd);
        let id = TrackPopupMenu(
            hmenu,
            TRACK_POPUP_MENU_FLAGS(flags) | TPM_RETURNCMD,
            x,
            y,
            0,
            hwnd,
            None,
        );
        let _ = PostMessageW(hwnd, 0, WPARAM(0), LPARAM(0));
        let _ = DestroyMenu(hmenu);
        id.0 as u32
    });
    Ok(selected)
}

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

thread_local! {
    static TRAY_V2: RefCell<Option<TrayIcon>> = const { RefCell::new(None) };
    static TRAY_V2_TID: RefCell<u32> = const { RefCell::new(0) };
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
    let rgba: Vec<u8> = (0..32u32 * 32u32)
        .flat_map(|_| [0u8, 122, 204, 255])
        .collect();
    tray_icon::Icon::from_rgba(rgba, 32, 32).expect("fallback icon")
}

#[pyfunction]
#[pyo3(signature = (tooltip, items, icon_path=None))]
pub fn tray_v2_create(
    tooltip: String,
    items: Vec<(String, String, bool)>,
    icon_path: Option<String>,
) -> PyResult<()> {
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
        .with_menu_on_left_click(false)
        .build()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    use windows::Win32::System::Threading::GetCurrentThreadId;
    TRAY_V2_TID.with(|t| *t.borrow_mut() = unsafe { GetCurrentThreadId() });
    TRAY_V2.with(|t| *t.borrow_mut() = Some(tray));
    Ok(())
}

#[pyfunction]
pub fn tray_v2_poll_event(py: Python<'_>) -> PyResult<Option<(String, String)>> {
    py.allow_threads(|| {
        let t_recv = TrayIconEvent::receiver();
        let m_recv = MenuEvent::receiver();

        loop {
            let mut msg = MSG::default();
            let got = unsafe { GetMessageW(&mut msg, None, 0, 0) };
            if !got.as_bool() {
                return Ok(None);
            }

            unsafe {
                let _ = TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }

            if let Ok(event) = t_recv.try_recv() {
                let kind = match &event {
                    TrayIconEvent::Click {
                        button,
                        button_state,
                        ..
                    } => match (button, button_state) {
                        (MouseButton::Left, MouseButtonState::Up) => "left_click",
                        (MouseButton::Right, MouseButtonState::Up) => "right_click",
                        _ => "unknown",
                    },
                    TrayIconEvent::DoubleClick { .. } => "double_click",
                    _ => "unknown",
                };
                return Ok(Some((kind.to_string(), String::new())));
            }

            if let Ok(event) = m_recv.try_recv() {
                return Ok(Some(("menu".to_string(), event.id.0.clone())));
            }
        }
    })
}

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

#[pyfunction]
pub fn tray_v2_destroy() -> PyResult<()> {
    TRAY_V2.with(|t| *t.borrow_mut() = None);
    Ok(())
}
