/// macOS system tray via NSStatusBar.
///
/// The Windows tray API is built around a Win32 message pump.  Here we
/// replicate the same shape using a Mutex<VecDeque> as the message queue so
/// that Python's tray.py event loop works identically on all three platforms:
///
///   while True:
///       msg = pytron_os.tray_get_message_ex()   # blocks until event
///       if msg is None:  break                  # WM_QUIT
///       handle(msg)
///
/// NSRunLoop is driven inside tray_get_message_ex() so AppKit callbacks fire.

use pyo3::prelude::*;
use objc::{class, declare::ClassDecl, msg_send, runtime::{Object, Sel}, sel, sel_impl};
use cocoa::base::{id, nil};
use once_cell::sync::Lazy;
use dashmap::DashMap;
use std::sync::{Mutex, Condvar};
use std::collections::VecDeque;
use std::ffi::CStr;

// ─── Platform message queue ──────────────────────────────────────────────────

pub struct MsgQ {
    pub deque: Mutex<VecDeque<(usize, u32, usize, isize)>>,
    pub cv:    Condvar,
}

pub static TRAY_MSG_QUEUE: Lazy<MsgQ> = Lazy::new(|| MsgQ {
    deque: Mutex::new(VecDeque::new()),
    cv:    Condvar::new(),
});

// Convenience: push a message and wake any waiter
fn push_msg(hwnd: usize, msg: u32, wp: usize, lp: isize) {
    if let Ok(mut q) = TRAY_MSG_QUEUE.deque.lock() {
        q.push_back((hwnd, msg, wp, lp));
        TRAY_MSG_QUEUE.cv.notify_one();
    }
}

// ─── Stored tray state ───────────────────────────────────────────────────────

struct TrayState {
    status_item: usize, // NSStatusItem*
    delegate:    usize, // PytronTrayDelegate*
}

static TRAY_STATE: Lazy<DashMap<usize, TrayState>> = Lazy::new(DashMap::new);

// ─── ObjC delegate class ─────────────────────────────────────────────────────

extern "C" fn item_clicked(this: &Object, _sel: Sel, _sender: id) {
    // WM_RBUTTONUP = 0x0205 signals right/left click to Python
    let hwnd_val: usize = unsafe { *this.get_ivar("registeredHwnd") };
    push_msg(hwnd_val, 0x0205, 0, 0);
}

// Store class pointer as usize to satisfy Send+Sync required by Lazy
static DELEGATE_CLASS: Lazy<usize> = Lazy::new(|| {
    let mut decl = ClassDecl::new("PytronTrayDelegate", class!(NSObject)).unwrap();
    decl.add_ivar::<usize>("registeredHwnd");
    unsafe {
        decl.add_method(sel!(itemClicked:), item_clicked as extern "C" fn(&Object, Sel, id));
    }
    decl.register() as usize
});

// ─── Helpers ─────────────────────────────────────────────────────────────────

unsafe fn nsstring(s: &str) -> id {
    let bytes = s.as_bytes();
    let ns: id = msg_send![class!(NSString), alloc];
    msg_send![ns, initWithBytes:bytes.as_ptr() length:bytes.len() encoding:4u64]
}

// WM_QUIT constant (same as Windows so Python code is portable)
const WM_QUIT: u32 = 0x0012;

// ─── tray_create_window ───────────────────────────────────────────────────────

/// On macOS the "hidden window" is the NSStatusItem itself.
/// Returns a fake HWND that Python stores and passes back to us.
#[pyfunction]
pub fn tray_create_window(_class_name: String, _title: String) -> PyResult<usize> {
    // Return a unique fake handle — we use 1 since there's only one status bar
    Ok(1)
}

// ─── Event pump ──────────────────────────────────────────────────────────────

/// Blocking equivalent of Win32 GetMessageW.
/// Runs NSRunLoop in short bursts and returns the first queued message.
/// Returns None when WM_QUIT is received.
#[pyfunction]
pub fn tray_get_message_ex(py: Python<'_>) -> PyResult<Option<(usize, u32, usize, isize)>> {
    let result = py.allow_threads(|| {
        loop {
            // Check queue
            let msg = {
                let mut q = TRAY_MSG_QUEUE.deque.lock().unwrap();
                q.pop_front()
            };
            if let Some(m) = msg {
                return m;
            }
            // Drive NSRunLoop for 20 ms so AppKit events fire
            unsafe {
                let rl: id = msg_send![class!(NSRunLoop), currentRunLoop];
                let mode = nsstring("NSDefaultRunLoopMode");
                let date: id = msg_send![class!(NSDate), dateWithTimeIntervalSinceNow: 0.02_f64];
                let _: u8 = msg_send![rl, runMode: mode beforeDate: date];
            }
        }
    });
    if result.1 == WM_QUIT {
        Ok(None)
    } else {
        Ok(Some(result))
    }
}

#[pyfunction]
pub fn tray_translate_dispatch(_hwnd_val: usize, _msg: u32, _wparam: usize, _lparam: isize) -> PyResult<()> {
    Ok(()) // NSRunLoop handles dispatch
}

// ─── Icon lifecycle ───────────────────────────────────────────────────────────

/// Create a macOS status-bar item.  hicon_val is an NSImage* (or 0 for default).
#[pyfunction]
pub fn tray_add_icon(hwnd_val: usize, hicon_val: usize, _id: u32, tip: String, _callback_msg: u32) -> PyResult<bool> {
    unsafe {
        let bar: id    = msg_send![class!(NSStatusBar), systemStatusBar];
        // NSVariableStatusItemLength = -1.0
        let item: id   = msg_send![bar, statusItemWithLength: -1.0_f64];
        let _: ()      = msg_send![item, retain]; // keep alive

        // Set tooltip
        let tip_ns = nsstring(&tip);
        let button: id = msg_send![item, button];
        let _: ()      = msg_send![button, setToolTip: tip_ns];

        // Set icon if provided
        if hicon_val != 0 {
            let image = hicon_val as id;
            let _: () = msg_send![image, setSize: [16.0_f64, 16.0_f64]];
            let _: () = msg_send![button, setImage: image];
        }

        // Create & attach delegate
        let cls   = unsafe { &*(*DELEGATE_CLASS as *const objc::runtime::Class) };
        let del: id = msg_send![cls, new];
        (*del).set_ivar("registeredHwnd", hwnd_val);

        let _: () = msg_send![button, setTarget: del];
        let _: () = msg_send![button, setAction: sel!(itemClicked:)];
        let _: () = msg_send![del, retain];

        TRAY_STATE.insert(hwnd_val, TrayState {
            status_item: item as usize,
            delegate: del as usize,
        });
        Ok(true)
    }
}

#[pyfunction]
pub fn tray_remove_icon(hwnd_val: usize, _id: u32) -> PyResult<()> {
    if let Some((_, state)) = TRAY_STATE.remove(&hwnd_val) {
        unsafe {
            let bar: id  = msg_send![class!(NSStatusBar), systemStatusBar];
            let item = state.status_item as id;
            let _: ()    = msg_send![bar, removeStatusItem: item];
        }
    }
    Ok(())
}

#[pyfunction]
pub fn tray_destroy_window(_hwnd_val: usize) -> PyResult<()> {
    Ok(()) // NSStatusItem removal handled by tray_remove_icon
}

#[pyfunction]
pub fn tray_post_message(hwnd_val: usize, msg: u32, wparam: usize, lparam: isize) -> PyResult<()> {
    push_msg(hwnd_val, msg, wparam, lparam);
    Ok(())
}

// ─── Icon loading ─────────────────────────────────────────────────────────────

/// Load an icon from file. Returns NSImage* as usize.
#[pyfunction]
pub fn tray_load_icon(path: String, _w: i32, _h: i32) -> PyResult<usize> {
    unsafe {
        let path_ns = nsstring(&path);
        let image: id = msg_send![class!(NSImage), alloc];
        let image: id = msg_send![image, initWithContentsOfFile: path_ns];
        if image.is_null() {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to load image"));
        }
        let _: () = msg_send![image, retain];
        Ok(image as usize)
    }
}

/// Returns the default NSApplicationIcon.
#[pyfunction]
pub fn tray_load_default_icon() -> PyResult<usize> {
    unsafe {
        let ns_app: id   = msg_send![class!(NSApplication), sharedApplication];
        let icon: id     = msg_send![ns_app, applicationIconImage];
        let _: ()        = msg_send![icon, retain];
        Ok(icon as usize)
    }
}

#[pyfunction]
pub fn tray_destroy_icon(hicon_val: usize) -> PyResult<()> {
    if hicon_val != 0 {
        unsafe {
            let image = hicon_val as id;
            let _: () = msg_send![image, release];
        }
    }
    Ok(())
}

// ─── Context menu ─────────────────────────────────────────────────────────────

/// Create an NSMenu. Returns NSMenu* as usize.
#[pyfunction]
pub fn tray_create_popup_menu() -> PyResult<usize> {
    unsafe {
        let menu: id = msg_send![class!(NSMenu), new];
        let _: ()    = msg_send![menu, setAutoenablesItems: 0_i8];
        let _: ()    = msg_send![menu, retain];
        Ok(menu as usize)
    }
}

#[pyfunction]
pub fn tray_append_menu_item(hmenu_val: usize, _flags: u32, id: u32, label: String) -> PyResult<()> {
    unsafe {
        let menu  = hmenu_val as id;
        let title = nsstring(&label);
        let item: id = msg_send![class!(NSMenuItem), alloc];
        // store id in tag
        let item: id = msg_send![item, initWithTitle:title action:sel!(itemClicked:) keyEquivalent:nsstring("")];
        let _: ()    = msg_send![item, setTag: id as isize];
        let _: ()    = msg_send![menu, addItem: item];
    }
    Ok(())
}

#[pyfunction]
pub fn tray_append_separator(hmenu_val: usize) -> PyResult<()> {
    unsafe {
        let menu = hmenu_val as id;
        let sep: id = msg_send![class!(NSMenuItem), separatorItem];
        let _: ()   = msg_send![menu, addItem: sep];
    }
    Ok(())
}

/// Display the menu beside the status item.
#[pyfunction]
pub fn tray_track_popup_menu(hmenu_val: usize, _flags: u32, _x: i32, _y: i32, hwnd_val: usize) -> PyResult<()> {
    if let Some(state) = TRAY_STATE.get(&hwnd_val) {
        unsafe {
            let item = state.status_item as id;
            let menu = hmenu_val as id;
            let _: () = msg_send![item, setMenu: menu];
            // Pop-up immediately then clear so next right-click re-shows
            let _: () = msg_send![item, popUpStatusItemMenu: menu];
            let _: () = msg_send![item, setMenu: nil];
        }
    }
    Ok(())
}

#[pyfunction]
pub fn tray_get_cursor_pos() -> PyResult<(i32, i32)> {
    // NSEvent.mouseLocation — returns NSPoint in screen coords
    unsafe {
        let loc: [f64; 2] = msg_send![class!(NSEvent), mouseLocation];
        Ok((loc[0] as i32, loc[1] as i32))
    }
}
