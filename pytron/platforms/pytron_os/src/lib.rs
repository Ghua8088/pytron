use pyo3::prelude::*;

#[cfg(target_os = "windows")]
mod win;

#[cfg(target_os = "macos")]
mod mac;

#[cfg(target_os = "linux")]
mod linux;

#[pymodule]
fn pytron_os(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    #[cfg(target_os = "windows")]
    {
        // --- window ---
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
        m.add_function(wrap_pyfunction!(win::set_border_color, m)?)?;
        m.add_function(wrap_pyfunction!(win::set_window_icon, m)?)?;
        m.add_function(wrap_pyfunction!(win::set_fullscreen, m)?)?;
        m.add_function(wrap_pyfunction!(win::show_notification, m)?)?;
        m.add_function(wrap_pyfunction!(win::set_app_id, m)?)?;
        m.add_function(wrap_pyfunction!(win::set_launch_on_boot, m)?)?;
        // --- taskbar ---
        m.add_function(wrap_pyfunction!(win::set_taskbar_progress, m)?)?;
        // --- clipboard ---
        m.add_function(wrap_pyfunction!(win::set_clipboard_text, m)?)?;
        m.add_function(wrap_pyfunction!(win::get_clipboard_text, m)?)?;
        // --- dialogs ---
        m.add_function(wrap_pyfunction!(win::message_box, m)?)?;
        m.add_function(wrap_pyfunction!(win::open_file_dialog, m)?)?;
        m.add_function(wrap_pyfunction!(win::open_folder_dialog, m)?)?;
        m.add_function(wrap_pyfunction!(win::save_file_dialog, m)?)?;
        // --- hotkeys ---
        m.add_function(wrap_pyfunction!(win::register_hotkey, m)?)?;
        m.add_function(wrap_pyfunction!(win::unregister_hotkey, m)?)?;
        // --- message loop ---
        m.add_function(wrap_pyfunction!(win::get_current_thread_id, m)?)?;
        m.add_function(wrap_pyfunction!(win::post_thread_message, m)?)?;
        m.add_function(wrap_pyfunction!(win::get_message, m)?)?;
        m.add_function(wrap_pyfunction!(win::init_message_queue, m)?)?;
        m.add_function(wrap_pyfunction!(win::translate_dispatch, m)?)?;
        // --- tray ---
        m.add_function(wrap_pyfunction!(win::tray_create_window, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_get_message_ex, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_translate_dispatch, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_add_icon, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_remove_icon, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_destroy_window, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_post_message, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_load_icon, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_load_default_icon, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_destroy_icon, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_create_popup_menu, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_append_menu_item, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_append_separator, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_track_popup_menu, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_get_cursor_pos, m)?)?;
        // --- tray v2 (tray-icon crate) ---
        m.add_function(wrap_pyfunction!(win::tray_v2_create, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_v2_poll_event, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_v2_interrupt, m)?)?;
        m.add_function(wrap_pyfunction!(win::tray_v2_destroy, m)?)?;
        // --- console ---
        m.add_function(wrap_pyfunction!(win::set_console_utf8, m)?)?;
    }

    #[cfg(target_os = "macos")]
    {
        // --- window ---
        m.add_function(wrap_pyfunction!(mac::set_utility_window, m)?)?;
        m.add_function(wrap_pyfunction!(mac::make_frameless, m)?)?;
        m.add_function(wrap_pyfunction!(mac::minimize, m)?)?;
        m.add_function(wrap_pyfunction!(mac::set_bounds, m)?)?;
        m.add_function(wrap_pyfunction!(mac::close, m)?)?;
        m.add_function(wrap_pyfunction!(mac::toggle_maximize, m)?)?;
        m.add_function(wrap_pyfunction!(mac::set_always_on_top, m)?)?;
        m.add_function(wrap_pyfunction!(mac::start_drag, m)?)?;
        m.add_function(wrap_pyfunction!(mac::hide, m)?)?;
        m.add_function(wrap_pyfunction!(mac::is_visible, m)?)?;
        m.add_function(wrap_pyfunction!(mac::show, m)?)?;
        m.add_function(wrap_pyfunction!(mac::center, m)?)?;
        m.add_function(wrap_pyfunction!(mac::set_border_color, m)?)?;
        m.add_function(wrap_pyfunction!(mac::set_window_icon, m)?)?;
        m.add_function(wrap_pyfunction!(mac::set_fullscreen, m)?)?;
        m.add_function(wrap_pyfunction!(mac::show_notification, m)?)?;
        m.add_function(wrap_pyfunction!(mac::set_taskbar_progress, m)?)?;
        m.add_function(wrap_pyfunction!(mac::set_app_id, m)?)?;
        m.add_function(wrap_pyfunction!(mac::set_launch_on_boot, m)?)?;
        // --- clipboard ---
        m.add_function(wrap_pyfunction!(mac::set_clipboard_text, m)?)?;
        m.add_function(wrap_pyfunction!(mac::get_clipboard_text, m)?)?;
        // --- dialogs ---
        m.add_function(wrap_pyfunction!(mac::message_box, m)?)?;
        m.add_function(wrap_pyfunction!(mac::open_file_dialog, m)?)?;
        m.add_function(wrap_pyfunction!(mac::open_folder_dialog, m)?)?;
        m.add_function(wrap_pyfunction!(mac::save_file_dialog, m)?)?;
        // --- hotkeys ---
        m.add_function(wrap_pyfunction!(mac::register_hotkey, m)?)?;
        m.add_function(wrap_pyfunction!(mac::unregister_hotkey, m)?)?;
        // --- message loop ---
        m.add_function(wrap_pyfunction!(mac::get_current_thread_id, m)?)?;
        m.add_function(wrap_pyfunction!(mac::post_thread_message, m)?)?;
        m.add_function(wrap_pyfunction!(mac::get_message, m)?)?;
        m.add_function(wrap_pyfunction!(mac::init_message_queue, m)?)?;
        m.add_function(wrap_pyfunction!(mac::translate_dispatch, m)?)?;
        // --- tray ---
        m.add_function(wrap_pyfunction!(mac::tray_create_window, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_get_message_ex, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_translate_dispatch, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_add_icon, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_remove_icon, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_destroy_window, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_post_message, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_load_icon, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_load_default_icon, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_destroy_icon, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_create_popup_menu, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_append_menu_item, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_append_separator, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_track_popup_menu, m)?)?;
        m.add_function(wrap_pyfunction!(mac::tray_get_cursor_pos, m)?)?;
        // --- console ---
        m.add_function(wrap_pyfunction!(mac::set_console_utf8, m)?)?;
    }

    #[cfg(target_os = "linux")]
    {
        // --- window ---
        m.add_function(wrap_pyfunction!(linux::set_utility_window, m)?)?;
        m.add_function(wrap_pyfunction!(linux::make_frameless, m)?)?;
        m.add_function(wrap_pyfunction!(linux::minimize, m)?)?;
        m.add_function(wrap_pyfunction!(linux::set_bounds, m)?)?;
        m.add_function(wrap_pyfunction!(linux::close, m)?)?;
        m.add_function(wrap_pyfunction!(linux::toggle_maximize, m)?)?;
        m.add_function(wrap_pyfunction!(linux::set_always_on_top, m)?)?;
        m.add_function(wrap_pyfunction!(linux::start_drag, m)?)?;
        m.add_function(wrap_pyfunction!(linux::hide, m)?)?;
        m.add_function(wrap_pyfunction!(linux::is_visible, m)?)?;
        m.add_function(wrap_pyfunction!(linux::show, m)?)?;
        m.add_function(wrap_pyfunction!(linux::center, m)?)?;
        m.add_function(wrap_pyfunction!(linux::set_border_color, m)?)?;
        m.add_function(wrap_pyfunction!(linux::set_window_icon, m)?)?;
        m.add_function(wrap_pyfunction!(linux::set_fullscreen, m)?)?;
        m.add_function(wrap_pyfunction!(linux::show_notification, m)?)?;
        m.add_function(wrap_pyfunction!(linux::set_taskbar_progress, m)?)?;
        m.add_function(wrap_pyfunction!(linux::set_app_id, m)?)?;
        m.add_function(wrap_pyfunction!(linux::set_launch_on_boot, m)?)?;
        // --- clipboard ---
        m.add_function(wrap_pyfunction!(linux::set_clipboard_text, m)?)?;
        m.add_function(wrap_pyfunction!(linux::get_clipboard_text, m)?)?;
        // --- dialogs ---
        m.add_function(wrap_pyfunction!(linux::message_box, m)?)?;
        m.add_function(wrap_pyfunction!(linux::open_file_dialog, m)?)?;
        m.add_function(wrap_pyfunction!(linux::open_folder_dialog, m)?)?;
        m.add_function(wrap_pyfunction!(linux::save_file_dialog, m)?)?;
        // --- hotkeys ---
        m.add_function(wrap_pyfunction!(linux::register_hotkey, m)?)?;
        m.add_function(wrap_pyfunction!(linux::unregister_hotkey, m)?)?;
        // --- message loop ---
        m.add_function(wrap_pyfunction!(linux::get_current_thread_id, m)?)?;
        m.add_function(wrap_pyfunction!(linux::post_thread_message, m)?)?;
        m.add_function(wrap_pyfunction!(linux::get_message, m)?)?;
        m.add_function(wrap_pyfunction!(linux::init_message_queue, m)?)?;
        m.add_function(wrap_pyfunction!(linux::translate_dispatch, m)?)?;
        // --- tray ---
        m.add_function(wrap_pyfunction!(linux::tray_create_window, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_get_message_ex, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_translate_dispatch, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_add_icon, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_remove_icon, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_destroy_window, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_post_message, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_load_icon, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_load_default_icon, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_destroy_icon, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_create_popup_menu, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_append_menu_item, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_append_separator, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_track_popup_menu, m)?)?;
        m.add_function(wrap_pyfunction!(linux::tray_get_cursor_pos, m)?)?;
        // --- console ---
        m.add_function(wrap_pyfunction!(linux::set_console_utf8, m)?)?;
    }

    Ok(())
}
