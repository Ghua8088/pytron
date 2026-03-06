use pyo3::prelude::*;
use windows::Win32::Foundation::HWND;
use windows::Win32::System::Com::{CoCreateInstance, CoInitialize, CLSCTX_INPROC_SERVER};
use windows::Win32::UI::Shell::{
    IFileOpenDialog, FileOpenDialog, IFileSaveDialog, FileSaveDialog,
    FOS_PICKFOLDERS, FOS_OVERWRITEPROMPT,
};

#[pyfunction]
pub fn message_box(py: Python<'_>, hwnd_val: usize, title: String, message: String, level: String) -> PyResult<i32> {
    let hwnd = HWND(hwnd_val as isize);
    let title_u16: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();
    let msg_u16:   Vec<u16> = message.encode_utf16().chain(std::iter::once(0)).collect();

    let level_flag = match level.as_str() {
        "error"   => windows::Win32::UI::WindowsAndMessaging::MB_ICONERROR,
        "warning" => windows::Win32::UI::WindowsAndMessaging::MB_ICONWARNING,
        _         => windows::Win32::UI::WindowsAndMessaging::MB_ICONINFORMATION,
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
#[pyo3(signature = (hwnd_val, title, _default_path=None, _file_types=None))]
pub fn open_file_dialog(py: Python<'_>, hwnd_val: usize, title: String, _default_path: Option<String>, _file_types: Option<String>) -> PyResult<Option<String>> {
    let hwnd = HWND(hwnd_val as isize);
    let title_u16: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();

    py.allow_threads(|| unsafe {
        let _ = CoInitialize(None);
        let dialog: IFileOpenDialog = CoCreateInstance(&FileOpenDialog, None, CLSCTX_INPROC_SERVER)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        let _ = dialog.SetTitle(windows::core::PCWSTR(title_u16.as_ptr()));

        if dialog.Show(hwnd).is_ok() {
            let result = dialog.GetResult()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            let path = result.GetDisplayName(windows::Win32::UI::Shell::SIGDN_FILESYSPATH)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            return Ok(Some(path.to_string()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?));
        }
        Ok(None)
    })
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, _default_path=None))]
pub fn open_folder_dialog(py: Python<'_>, hwnd_val: usize, title: String, _default_path: Option<String>) -> PyResult<Option<String>> {
    let hwnd = HWND(hwnd_val as isize);
    let title_u16: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();

    py.allow_threads(|| unsafe {
        let _ = CoInitialize(None);
        let dialog: IFileOpenDialog = CoCreateInstance(&FileOpenDialog, None, CLSCTX_INPROC_SERVER)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        let _ = dialog.SetTitle(windows::core::PCWSTR(title_u16.as_ptr()));
        let _ = dialog.SetOptions(FOS_PICKFOLDERS);

        if dialog.Show(hwnd).is_ok() {
            let result = dialog.GetResult()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            let path = result.GetDisplayName(windows::Win32::UI::Shell::SIGDN_FILESYSPATH)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            return Ok(Some(path.to_string()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?));
        }
        Ok(None)
    })
}

#[pyfunction]
#[pyo3(signature = (hwnd_val, title, _default_path=None, _default_name=None, _file_types=None))]
pub fn save_file_dialog(py: Python<'_>, hwnd_val: usize, title: String, _default_path: Option<String>, _default_name: Option<String>, _file_types: Option<String>) -> PyResult<Option<String>> {
    let hwnd = HWND(hwnd_val as isize);
    let title_u16: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();

    py.allow_threads(|| unsafe {
        let _ = CoInitialize(None);
        let dialog: IFileSaveDialog = CoCreateInstance(&FileSaveDialog, None, CLSCTX_INPROC_SERVER)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        let _ = dialog.SetTitle(windows::core::PCWSTR(title_u16.as_ptr()));
        let _ = dialog.SetOptions(FOS_OVERWRITEPROMPT);

        if dialog.Show(hwnd).is_ok() {
            let result = dialog.GetResult()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            let path = result.GetDisplayName(windows::Win32::UI::Shell::SIGDN_FILESYSPATH)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            return Ok(Some(path.to_string()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?));
        }
        Ok(None)
    })
}
