use pyo3::prelude::*;
use rfd::FileDialog;
use raw_window_handle::{HasWindowHandle, RawWindowHandle, Win32WindowHandle, WindowHandle};
use windows::Win32::Foundation::HWND;

struct HwndWrapper(HWND);

impl HasWindowHandle for HwndWrapper {
    fn window_handle(&self) -> Result<WindowHandle<'_>, raw_window_handle::HandleError> {
        let handle = Win32WindowHandle::new(std::num::NonZeroIsize::new(self.0 .0).unwrap());
        Ok(unsafe { WindowHandle::borrow_raw(RawWindowHandle::Win32(handle)) })
    }
}

#[pyfunction]
pub fn message_box(
    py: Python<'_>,
    hwnd_val: usize,
    title: String,
    message: String,
    level: String,
) -> PyResult<i32> {
    let hwnd = HWND(hwnd_val as isize);
    let title_u16: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();
    let msg_u16: Vec<u16> = message.encode_utf16().chain(std::iter::once(0)).collect();

    let level_flag = match level.as_str() {
        "error" => windows::Win32::UI::WindowsAndMessaging::MB_ICONERROR,
        "warning" => windows::Win32::UI::WindowsAndMessaging::MB_ICONWARNING,
        _ => windows::Win32::UI::WindowsAndMessaging::MB_ICONINFORMATION,
    };

    let res = py.allow_threads(|| unsafe {
        windows::Win32::UI::WindowsAndMessaging::MessageBoxW(
            hwnd,
            windows::core::PCWSTR(msg_u16.as_ptr()),
            windows::core::PCWSTR(title_u16.as_ptr()),
            level_flag,
        )
    });
    Ok(res.0)
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, default_path=None, _file_types=None))]
pub fn open_file_dialog(
    py: Python<'_>,
    hwnd_val: usize,
    title: String,
    default_path: Option<String>,
    _file_types: Option<PyObject>,
) -> PyResult<Option<String>> {
    let mut dialog = FileDialog::new().set_title(&title);
    if let Some(path) = default_path {
        dialog = dialog.set_directory(path);
    }
    
    if hwnd_val != 0 {
        if let Some(parent) = std::num::NonZeroIsize::new(hwnd_val as isize) {
             dialog = dialog.set_parent(&HwndWrapper(HWND(parent.get())));
        }
    }
    
    let res = py.allow_threads(|| {
        dialog.pick_file().map(|p| p.to_string_lossy().to_string())
    });
    Ok(res)
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, default_path=None))]
pub fn open_folder_dialog(
    py: Python<'_>,
    hwnd_val: usize,
    title: String,
    default_path: Option<String>,
) -> PyResult<Option<String>> {
    let mut dialog = FileDialog::new().set_title(&title);
    if let Some(path) = default_path {
        dialog = dialog.set_directory(path);
    }
    
    if hwnd_val != 0 {
        if let Some(parent) = std::num::NonZeroIsize::new(hwnd_val as isize) {
             dialog = dialog.set_parent(&HwndWrapper(HWND(parent.get())));
        }
    }
    
    let res = py.allow_threads(|| {
        dialog.pick_folder().map(|p| p.to_string_lossy().to_string())
    });
    Ok(res)
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, default_path=None, default_name=None, _file_types=None))]
pub fn save_file_dialog(
    py: Python<'_>,
    hwnd_val: usize,
    title: String,
    default_path: Option<String>,
    default_name: Option<String>,
    _file_types: Option<PyObject>,
) -> PyResult<Option<String>> {
    let mut dialog = FileDialog::new().set_title(&title);
    if let Some(path) = default_path {
        dialog = dialog.set_directory(path);
    }
    if let Some(name) = default_name {
        dialog = dialog.set_file_name(name);
    }
    
    if hwnd_val != 0 {
        if let Some(parent) = std::num::NonZeroIsize::new(hwnd_val as isize) {
             dialog = dialog.set_parent(&HwndWrapper(HWND(parent.get())));
        }
    }
    
    let res = py.allow_threads(|| {
        dialog.save_file().map(|p| p.to_string_lossy().to_string())
    });
    Ok(res)
}
