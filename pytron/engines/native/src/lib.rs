use pyo3::prelude::*;

pub mod events;
pub mod ipc;
pub mod protocol;
pub mod state;
pub mod store;
pub mod utils;
pub mod webview;
pub mod os_hooks;
#[cfg(target_os = "windows")]
pub use os_hooks as winhooks; // Alias for backward compatibility in this file

use crate::ipc::ChromeIPC;
use crate::store::NativeState;
use crate::webview::NativeWebview;

#[pymodule]
fn pytron_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<NativeWebview>()?;
    m.add_class::<ChromeIPC>()?;
    m.add_class::<NativeState>()?;

    m.add_function(wrap_pyfunction!(os_hooks::set_utility_window, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::make_frameless, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::maximize, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::restore, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::set_title, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::minimize, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::set_bounds, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::close, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::toggle_maximize, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::set_always_on_top, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::start_drag, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::hide, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::is_visible, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::show, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::center, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::set_border_color, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::set_window_icon, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::set_fullscreen, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::show_notification, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::set_app_id, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::set_launch_on_boot, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::set_taskbar_progress, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::set_clipboard_text, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::get_clipboard_text, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::message_box, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::open_file_dialog, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::open_folder_dialog, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::save_file_dialog, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::register_hotkey, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::unregister_hotkey, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::get_current_thread_id, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::post_thread_message, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::get_message, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::init_message_queue, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::translate_dispatch, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_create_window, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_get_message_ex, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_translate_dispatch, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_add_icon, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_remove_icon, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_destroy_window, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_post_message, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_load_icon, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_load_default_icon, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_destroy_icon, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_create_popup_menu, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_append_menu_item, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_append_separator, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_track_popup_menu, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_get_cursor_pos, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_v2_create, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_v2_poll_event, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_v2_interrupt, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::tray_v2_destroy, m)?)?;
    m.add_function(wrap_pyfunction!(os_hooks::set_console_utf8, m)?)?;

    Ok(())
}
