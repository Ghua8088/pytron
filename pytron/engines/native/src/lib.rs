use pyo3::prelude::*;

pub mod events;
pub mod ipc;
pub mod protocol;
pub mod state;
pub mod store;
pub mod utils;
pub mod webview;
#[cfg(target_os = "windows")]
pub mod winhooks;

use crate::ipc::ChromeIPC;
use crate::store::NativeState;
use crate::webview::NativeWebview;

#[pymodule]
fn pytron_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<NativeWebview>()?;
    m.add_class::<ChromeIPC>()?;
    m.add_class::<NativeState>()?;

    #[cfg(target_os = "windows")]
    {
        m.add_function(wrap_pyfunction!(winhooks::set_utility_window, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::make_frameless, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::minimize, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::set_bounds, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::close, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::toggle_maximize, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::set_always_on_top, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::start_drag, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::hide, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::is_visible, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::show, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::center, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::set_border_color, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::set_window_icon, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::set_fullscreen, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::show_notification, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::set_app_id, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::set_launch_on_boot, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::set_taskbar_progress, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::set_clipboard_text, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::get_clipboard_text, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::message_box, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::open_file_dialog, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::open_folder_dialog, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::save_file_dialog, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::register_hotkey, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::unregister_hotkey, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::get_current_thread_id, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::post_thread_message, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::get_message, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::init_message_queue, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::translate_dispatch, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_create_window, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_get_message_ex, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_translate_dispatch, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_add_icon, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_remove_icon, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_destroy_window, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_post_message, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_load_icon, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_load_default_icon, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_destroy_icon, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_create_popup_menu, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_append_menu_item, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_append_separator, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_track_popup_menu, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_get_cursor_pos, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_v2_create, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_v2_poll_event, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_v2_interrupt, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::tray_v2_destroy, m)?)?;
        m.add_function(wrap_pyfunction!(winhooks::set_console_utf8, m)?)?;
    }

    Ok(())
}
