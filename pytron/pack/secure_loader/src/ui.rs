use rfd::{MessageButtons, MessageLevel, MessageDialog};

#[cfg(windows)]
extern crate winapi;

pub fn alert(title: &str, message: &str) {
    MessageDialog::new()
        .set_title(title)
        .set_description(message)
        .set_buttons(MessageButtons::Ok)
        .set_level(MessageLevel::Error)
        .show();
}

pub fn set_app_id(_id: &str) {
    #[cfg(windows)]
    unsafe {
        let id = _id;
        use std::os::windows::ffi::OsStrExt;
        let id_wide: Vec<u16> = std::ffi::OsStr::new(id).encode_wide().chain(Some(0)).collect();
        
        let shell32 = winapi::um::libloaderapi::GetModuleHandleA(b"shell32.dll\0".as_ptr() as *const i8);
        if !shell32.is_null() {
            let func_name = b"SetCurrentProcessExplicitAppUserModelID\0";
            let addr = winapi::um::libloaderapi::GetProcAddress(shell32, func_name.as_ptr() as *const i8);
            if !addr.is_null() {
                let func: unsafe extern "system" fn(*const u16) -> i32 = std::mem::transmute(addr);
                func(id_wide.as_ptr());
            }
        }
    }
}

pub fn init_com() {
    #[cfg(windows)]
    unsafe {
        winapi::um::objbase::CoInitialize(std::ptr::null_mut());
    }
}

