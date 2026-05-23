use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::path::PathBuf;

use tao::{
    event::{Event, WindowEvent},
    event_loop::{ControlFlow, EventLoopBuilder, EventLoopProxy, EventLoop},
    window::WindowBuilder,
};
#[cfg(not(target_os = "android"))]
// tray_icon removed — tray owned by pytron_os
use wry::WebViewBuilder;

#[cfg(target_os = "windows")]
use wry::WebViewBuilderExtWindows; 
#[cfg(target_os = "windows")]
use tao::platform::windows::EventLoopBuilderExtWindows;

use crate::events::UserEvent;
use crate::state::RuntimeState;
use crate::utils::{setup_panic_hook, SendWrapper};
use crate::protocol::handle_pytron_protocol;

use crate::store::NativeState;

#[pyclass]
pub struct NativeWebview {
    pub proxy: EventLoopProxy<UserEvent>,
    runner: Mutex<Option<EventLoop<UserEvent>>>,
    state_ptr: Mutex<Option<usize>>, 
    hwnd: usize,
    callbacks: Arc<Mutex<HashMap<String, PyObject>>>,
    #[allow(dead_code)]
    store: NativeState,
    is_utility: Mutex<bool>,
}

unsafe impl Send for NativeWebview {}
unsafe impl Sync for NativeWebview {}

#[cfg(target_os = "linux")]
static TAO_INIT: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

#[pymethods]
impl NativeWebview {
    #[new]
    pub fn new(debug: bool, url_str: String, root_path: String, resizable: bool, frameless: bool, store: NativeState, initial_width: f64, initial_height: f64) -> PyResult<Self> {
    
        setup_panic_hook();

        let safe_url = if url_str == "about:blank" {
             url_str
        } else if url_str.starts_with("pytron://") {
             url_str
        } else if url_str.starts_with("http") {
             url_str
        } else if url_str.starts_with("data:") {
             url_str
        } else {
             format!("pytron://app/{}", url_str.trim_start_matches('/'))
        };

        println!("[PYTRON NATIVE] Init. Target: {} | Root: {}", safe_url, root_path);

        let mut builder = EventLoopBuilder::<UserEvent>::with_user_event();
        
        #[cfg(target_os = "windows")]
        {
            builder.with_any_thread(true);
        }

        #[cfg(target_os = "linux")]
        {
            // --- ATOMIC ISOLATION ---
            // We MUST set these before the EventLoop or Window is created.
            std::env::set_var("GSETTINGS_BACKEND", "memory");
            std::env::set_var("GIO_USE_VFS", "local");
            std::env::set_var("GIO_MODULE_DIR", "/nonexistent");
            std::env::set_var("NO_AT_BRIDGE", "1");
            
            // Force X11 on VMs for better stability/handle support.
            if std::env::var("WINIT_UNIX_BACKEND").is_err() {
                std::env::set_var("WINIT_UNIX_BACKEND", "x11");
            }
        }

        let event_loop = builder.build();
        let proxy = event_loop.create_proxy();
        
        // --- IRON BRIDGE: HOOK PROPAGATION ---
        store._bind_proxy(proxy.clone());
        
        let window = WindowBuilder::new()
            .with_title("Pytron App")
            // Linux: window must be visible so GTK realizes it (allocates the
            // GdkWindow handle) before wry tries to embed WebKit into it.
            .with_visible(cfg!(target_os = "linux"))
            .with_resizable(resizable)
            .with_decorations(!frameless);
            
        // --- PREVENT AUTO-SNAP TO (0,0) ON WINDOWS ---
        #[cfg(target_os = "windows")]
        let window = window.with_position(tao::dpi::LogicalPosition::new(-10000, -10000));
        
        let window = window.build(&event_loop)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create window: {}", e)))?;

        // FIX: Re-apply dimensions immediately after build while the window is still hidden/off-screen
        // but before the WebView is embedded. This ensures Wry embeds into a correctly sized container.
        window.set_inner_size(tao::dpi::LogicalSize::new(initial_width, initial_height));

        // Linux: workarounds for VMs and realization timing.
        #[cfg(target_os = "linux")]
        {
            // Disable hardware acceleration: critical for VMware/VirtualBox.
            if std::env::var("WEBKIT_DISABLE_COMPOSITING_MODE").is_err() {
                std::env::set_var("WEBKIT_DISABLE_COMPOSITING_MODE", "1");
            }
            
            // Give the window a moment to get realized on the X server.
            // Pumping the loop directly via glib crate causes symbol collisions with gi.
            std::thread::sleep(std::time::Duration::from_millis(10));
        }
        
        #[cfg(target_os = "windows")]
        let hwnd = {
            use tao::platform::windows::WindowExtWindows;
            window.hwnd() as usize
        };
        #[cfg(not(target_os = "windows"))]
        let hwnd = 0;

        let root = PathBuf::from(&root_path);
        let callbacks = Arc::new(Mutex::new(HashMap::<String, PyObject>::new()));
        let cbs_for_ipc = callbacks.clone();

        let mut builder = WebViewBuilder::new(&window)
            .with_devtools(debug)
            .with_url(&safe_url);

        // --- Custom Protocol Handler ---
        let protocol_root = root.clone();
        let cbs_for_protocol = callbacks.clone();
        
        builder = builder.with_custom_protocol("pytron".into(), move |request| {
            handle_pytron_protocol(request, protocol_root.clone(), cbs_for_protocol.clone())
        });
        
        #[cfg(target_os = "windows")]
        {
             builder = builder.with_https_scheme(true);
        }

        let proxy_for_nav = proxy.clone();
        builder = builder.with_navigation_handler(move |url: String| {
            // Relaxed for Dev Mode support (localhost/127.0.0.1)
            let is_safe = url.starts_with("pytron://") 
                || url.starts_with("https://pytron.") 
                || url == "about:blank"
                || url.starts_with("http://localhost")
                || url.starts_with("http://127.0.0.1")
                || url.starts_with("file://")
                || url.starts_with("data:");

            if !is_safe {
                // External! Send to system browser
                let _ = proxy_for_nav.send_event(UserEvent::OpenExternal(url.clone()));
                return false; // Prevent internal navigation
            }
            true // Allow internal navigation
        });

        let proxy_for_new_window = proxy.clone();
        builder = builder.with_new_window_req_handler(move |url: String| {
            // For new windows (target="_blank"), always prefer external browser
            let _ = proxy_for_new_window.send_event(UserEvent::OpenExternal(url.clone()));
            false // Prevent internal window creation
        });

        builder = builder.with_initialization_script(r#"
            window.pytron_is_native = true;
            
            // --- DE-BROWSERIFY CORE ---
            (function() {
                const isDebug = window.location.search.includes('debug=true') || window.__PYTRON_DEBUG__;
                
                // 1. Kill Context Menu (Unless debugging)
                if (!isDebug) {
                    document.addEventListener('contextmenu', e => e.preventDefault());
                }

                // 2. Kill "Ghost" Drags (images/links flying around)
                document.addEventListener('dragstart', e => {
                    if (e.target.tagName === 'IMG' || e.target.tagName === 'A') e.preventDefault();
                });

                // 3. Kill Browser Shortcuts
                window.addEventListener('keydown', e => {
                    const forbidden = ['r', 'p', 's', 'j', 'u', 'f'];
                    if (e.ctrlKey && forbidden.includes(e.key.toLowerCase())) e.preventDefault();
                    if (e.key === 'F5' || e.key === 'F3' || (e.ctrlKey && e.key === 'f')) e.preventDefault();
                    // Block Zoom
                    if (e.ctrlKey && (e.key === '=' || e.key === '-' || e.key === '0')) e.preventDefault();
                }, true);

                // 4. Kill System UI Styles (Selection, Outlines, Rubber-banding)
                const style = document.createElement('style');
                style.textContent = `
                    * { 
                        -webkit-user-select: none; 
                        user-select: none;
                        -webkit-user-drag: none; 
                        -webkit-tap-highlight-color: transparent;
                        outline: none !important;
                    }
                    input, textarea, [contenteditable], [contenteditable] * { 
                        -webkit-user-select: text !important; 
                        user-select: text !important;
                    }
                    html, body {
                        overscroll-behavior: none !important;
                        cursor: default;
                    }
                    a, button, input[type="button"], input[type="submit"] {
                        cursor: pointer;
                    }
                `;
                document.head ? document.head.appendChild(style) : document.addEventListener('DOMContentLoaded', () => document.head.appendChild(style));
            })();

            window.pytron = window.pytron || {};
            window.pytron.is_ready = true;
            window.__pytron_native_bridge = (method, args) => {
                const seq = Math.random().toString(36).substring(2, 10);
                const ipc = window.ipc || window.chrome?.webview || window.webkit?.messageHandlers?.ipc;
                if (ipc) {
                    ipc.postMessage(JSON.stringify({id: seq, method: method, params: args}));
                } else {
                    console.error("Pytron IPC not initialized.");
                }
                return new Promise((resolve, reject) => {
                    window._rpc = window._rpc || {};
                    window._rpc[seq] = {resolve, reject};
                });
            };

            // Dynamic Proxy for window.pytron.* calls
            window.pytron = new Proxy(window.pytron, {
                get: (target, prop) => {
                    if (prop in target) return target[prop];
                    return (...args) => window.__pytron_native_bridge(prop, args);
                }
            });

            window.pytron_close = () => window.__pytron_native_bridge('pytron_close', []);
            window.pytron_drag = () => window.__pytron_native_bridge('pytron_drag', []);
            window.pytron_log = (msg) => window.__pytron_native_bridge('pytron_log', [msg]);

            // Override alert to use native message box
            window.alert = (msg) => {
                window.__pytron_native_bridge('pytron_message_box', ["Alert", String(msg), "info"]);
            };
        "#);

        let proxy_for_ipc = proxy.clone();
        let store_for_ipc = store.clone();

        builder = builder.with_ipc_handler(move |request| {
            let msg = request.body().clone();
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&msg) {
                let seq = val["id"].as_str().unwrap_or("").to_string();
                let method = val["method"].as_str().unwrap_or("").to_string();
                let params = val["params"].to_string(); 
                
                // 1. Check Special Native Methods (Zero Overhead / Native Speed)
                if method == "pytron_drag" || method == "drag" {
                    let _ = proxy_for_ipc.send_event(UserEvent::DragWindow);
                    return;
                }

                // 2. AUTHORITATIVE NATIVE SYNC (Bypass Python Schism)
                if method == "pytron_close" || method == "close" || method == "app_quit" {
                    let _ = proxy_for_ipc.send_event(UserEvent::Quit);
                    return;
                }

                if method == "pytron_sync_state" {
                    let mut state_json = String::from("{}");
                    
                    // ACCESS RUST STORE DIRECTLY
                    let _ = Python::with_gil(|py| {
                        if let Ok(dict) = store_for_ipc.to_dict(py) {
                            if let Ok(json_mod) = py.import("json") {
                                if let Ok(res) = json_mod.call_method1("dumps", (dict,)) {
                                    if let Ok(s) = res.extract::<String>() {
                                        state_json = s;
                                    }
                                }
                            }
                        }
                    });

                    // println!("[SHIELD] Iron Bridge: sync_state (len={})", state_json.len());
                    let _ = proxy_for_ipc.send_event(UserEvent::Return(seq, 0, state_json));
                    return;
                }

                // system_notification and message_box fall through to CallPython → pytron_os.

                if method == "set_taskbar_progress" || method == "pytron_set_taskbar_progress" {
                    if let Ok(args) = serde_json::from_str::<Vec<i32>>(&params) {
                         if args.len() >= 3 {
                             let _ = proxy_for_ipc.send_event(UserEvent::TaskbarProgress(args[0], args[1], args[2]));
                             return;
                         }
                    }
                }

                // 2. Search for bound Python Functions
                let mut found_func: Option<PyObject> = None;
                if let Ok(cbs) = cbs_for_ipc.lock() {
                    if let Some(f) = cbs.get(&method) {
                        Python::with_gil(|py| { found_func = Some(f.clone_ref(py)); });
                    }
                }

                if let Some(func) = found_func {
                    let _ = proxy_for_ipc.send_event(UserEvent::CallPython(func, seq, params, method));
                } else {
                    // Method not found - return error to JS
                    let error_msg = format!("\"Method '{}' not found.\"", method);
                    let _ = proxy_for_ipc.send_event(UserEvent::Return(seq, 1, error_msg));
                }
            }
        });

        let webview = builder.build()
             .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to build WebView: {}", e)))?;

        // Re-hide on Linux after successful build so it stays hidden until explicitly shown
        #[cfg(target_os = "linux")]
        window.set_visible(false);

        let state = Box::into_raw(Box::new(RuntimeState { 
            webview, 
            window, 
            callbacks: callbacks.clone(),
            prevent_close: false,
            is_utility: false,
            store: store.clone(),
        }));

        Ok(NativeWebview {
            proxy,
            runner: Mutex::new(Some(event_loop)),
            state_ptr: Mutex::new(Some(state as usize)),
            hwnd,
            callbacks,
            store: store.clone(),
            is_utility: Mutex::new(false),
        })
    }

    pub fn run(&self, py: Python<'_>) -> PyResult<()> {
        let event_loop = self.runner.lock().unwrap().take();
        let state_ptr_val = self.state_ptr.lock().unwrap().take();

        if let (Some(el), Some(ptr)) = (event_loop, state_ptr_val) {
            let mut state = unsafe { Box::from_raw(ptr as *mut RuntimeState) };
            state.is_utility = *self.is_utility.lock().unwrap();
            
            let cbs_arc = state.callbacks.clone();
            let w_el = SendWrapper::new(el);
            let w_state = SendWrapper::new(state);

            py.allow_threads(move || {
                let el = w_el.take();
                let mut state = w_state.take();
                
                el.run(move |event, _, control_flow| {
                    *control_flow = ControlFlow::Wait;
                    
                    match event {
                        Event::UserEvent(ue) => {
                             // DEBUG LOGGING
                             match &ue {
                                 UserEvent::CallPython(_, seq, _, method) => {
                                     if !method.starts_with("inspector_") {
                                         println!("[PYTRON BRIDGE] CALL: {} (seq={})", method, seq);
                                     }
                                 },
                                 UserEvent::Eval(_) => { /* Mute eval logs, too spammy for state sync */ },
                                 UserEvent::Navigate(u) => println!("[PYTRON NAVIGATE] Request: '{}'", u),
                                 UserEvent::OpenDevtools => println!("[PYTRON DEVTOOLS] Open request"),
                                 UserEvent::Return(_seq, _status, _) => {
                                     // println!("[PYTRON BRIDGE] RETURN: seq={} status={}", seq, status);
                                 },
                                 _ => {},
                             }
                             
                             match ue {
                                UserEvent::Quit => {
                                    // IMMEDIATE UX IMPROVEMENT: Move window off-screen + Hide
                                    state.window.set_outer_position(tao::dpi::PhysicalPosition::new(-10000, -10000));
                                    state.window.set_visible(false);
                                    
                                    if !state.is_utility {
                                        *control_flow = ControlFlow::Exit;
                                    }
                                }
                                UserEvent::Eval(js) => { let _ = state.webview.evaluate_script(&js); }
                                UserEvent::SetTitle(t) => { state.window.set_title(&t); }
                                UserEvent::SetSize(w, h, _) => { state.window.set_inner_size(tao::dpi::LogicalSize::new(w, h)); }
                                UserEvent::SetBounds(x, y, w, h) => {
                                    if x != -1 && y != -1 {
                                        state.window.set_outer_position(tao::dpi::LogicalPosition::new(x, y));
                                    }
                                    state.window.set_inner_size(tao::dpi::LogicalSize::new(w, h));
                                }
                                
                                UserEvent::Navigate(u) => { 
                                    let _ = state.webview.load_url(&u);
                                }

                                UserEvent::OpenDevtools => {
                                    state.webview.open_devtools();
                                }

                                UserEvent::Bind(name, _) => {
                                    // Map is already updated in NativeWebview::bind
                                    let js = format!(r#"window['{}'] = (...args) => window.__pytron_native_bridge('{}', args);"#, name, name);
                                    let _ = state.webview.evaluate_script(&js);
                                }
                                UserEvent::CallPython(f, seq, args, _) => { 
                                    Python::with_gil(|py| { let _ = f.call1(py, (seq, args, 0)); }); 
                                }
                                UserEvent::Dispatch(f, seq, _) => { 
                                     Python::with_gil(|py| { let _ = f.call1(py, (seq, "[]", 0)); }); 
                                }
                                UserEvent::DispatchData(f, seq, args, _) => { 
                                     Python::with_gil(|py| { let _ = f.call1(py, (seq, args, 0)); }); 
                                }

                                UserEvent::Return(seq, status, res) => {
                                    let js = format!(r#"if (window._rpc && window._rpc['{seq}']) {{ if ({status} === 0) window._rpc['{seq}'].resolve({res}); else window._rpc['{seq}'].reject({res}); delete window._rpc['{seq}']; }}"#, seq=seq, status=status, res=res);
                                    let _ = state.webview.evaluate_script(&js);
                                }
                                UserEvent::SetVisible(v) => { 
                                    state.window.set_visible(v); 
                                    if v { 
                                        state.window.set_focus(); 
                                        state.window.set_minimized(false); 
                                    } 
                                }
                                UserEvent::Minimize => { state.window.set_minimized(true); }
                                UserEvent::SetMaximized(m) => { 
                                    if m {
                                         if !state.window.is_maximized() { state.window.set_maximized(true); }
                                    } else {
                                         state.window.set_maximized(false);
                                    }
                                }
                                UserEvent::DragWindow => { let _ = state.window.drag_window(); }
                                
                                UserEvent::SetAlwaysOnTop(t) => { state.window.set_always_on_top(t); }
                                UserEvent::SetResizable(r) => { state.window.set_resizable(r); }
                                UserEvent::SetFullscreen(f) => { 
                                    if f { state.window.set_fullscreen(Some(tao::window::Fullscreen::Borderless(None))); } 
                                    else { state.window.set_fullscreen(None); }
                                }
                                UserEvent::CenterWindow => {
                                     let monitor = state.window.current_monitor().or_else(|| state.window.primary_monitor());
                                     if let Some(monitor) = monitor {
                                         let screen_size = monitor.size();
                                         let monitor_pos = monitor.position();
                                         let mut window_size = state.window.outer_size();
                                         
                                         // Fallback if window size isn't realized yet (common for start_hidden: true)
                                         if window_size.width == 0 || window_size.height == 0 {
                                             window_size = tao::dpi::PhysicalSize::new(800, 600);
                                         }
                                         
                                         let x = monitor_pos.x + (screen_size.width as i32 - window_size.width as i32) / 2;
                                         let y = monitor_pos.y + (screen_size.height as i32 - window_size.height as i32) / 2;
                                         
                                         state.window.set_outer_position(tao::dpi::PhysicalPosition::new(x, y));
                                     }
                                }
                                
                                UserEvent::TaskbarProgress(state_code, val, _max) => {
                                    #[cfg(target_os = "windows")]
                                    {
                                        use tao::window::ProgressState;
                                        let s = match state_code {
                                            2 => ProgressState::Normal,
                                            4 => ProgressState::Error,
                                            8 => ProgressState::Paused,
                                            1 => ProgressState::Indeterminate,
                                            _ => ProgressState::None,
                                        };
                                        state.window.set_progress_bar(tao::window::ProgressBarState {
                                            state: Some(s),
                                            progress: Some(val as u64),
                                            desktop_filename: None,
                                        });
                                    }
                                    #[cfg(not(target_os = "windows"))]
                                    {
                                        let _ = (state_code, val, _max);
                                    }
                                }

                                UserEvent::SetDecorations(d) => { state.window.set_decorations(d); }

                                UserEvent::OpenExternal(url) => {
                                    #[cfg(target_os = "windows")]
                                    unsafe {
                                        use windows::Win32::UI::Shell::ShellExecuteW;
                                        use windows::Win32::Foundation::HWND;
                                        use windows::core::PCWSTR;
                                        use windows::Win32::UI::WindowsAndMessaging::SHOW_WINDOW_CMD;

                                        let url_wide: Vec<u16> = url.encode_utf16().chain(std::iter::once(0)).collect();
                                        let operation: Vec<u16> = "open".encode_utf16().chain(std::iter::once(0)).collect();
                                        
                                        ShellExecuteW(
                                            HWND(0),
                                            PCWSTR(operation.as_ptr()),
                                            PCWSTR(url_wide.as_ptr()),
                                            None,
                                            None,
                                            SHOW_WINDOW_CMD(1), // SW_SHOWNORMAL
                                        );
                                    }
                                    #[cfg(target_os = "macos")]
                                    {
                                        let _ = std::process::Command::new("open")
                                            .arg(&url)
                                            .spawn();
                                    }
                                    #[cfg(target_os = "linux")]
                                    {
                                        let _ = std::process::Command::new("xdg-open")
                                            .arg(&url)
                                            .spawn();
                                    }
                                }

                                UserEvent::StateUpdate(key, val) => {
                                    let js = format!(r#"window.dispatchEvent(new CustomEvent('pytron:state-update', {{ detail: {{ key: '{}', value: {} }} }}));"#, key, val);
                                    let _ = state.webview.evaluate_script(&js);
                                }

                                UserEvent::SetPreventClose(p) => {
                                    state.prevent_close = p;
                                }
                             }
                        }
                        
                        Event::WindowEvent { event: WindowEvent::CloseRequested, .. } => {
                             if state.prevent_close {
                                 let mut found: Option<PyObject> = None;
                                 if let Ok(cbs) = cbs_arc.lock() {
                                     if let Some(f) = cbs.get("pytron_on_close") {
                                         Python::with_gil(|py| { found = Some(f.clone_ref(py)); });
                                     }
                                 }
                                 if let Some(f) = found {
                                     Python::with_gil(|py| { let _ = f.call0(py); }); 
                                 }
                                 *control_flow = ControlFlow::Wait;
                             } else {
                                 // IMMEDIATE UX IMPROVEMENT: Hide + Zap off-screen
                                 state.window.set_outer_position(tao::dpi::PhysicalPosition::new(-10000, -10000));
                                 state.window.set_visible(false);
                                 
                                 if !state.is_utility {
                                     *control_flow = ControlFlow::Exit; 
                                 }
                             }
                        }
                        _ => (),
                    }
                });
            });
        }
        Ok(())
    }

    pub fn set_title(&self, t: String) { let _ = self.proxy.send_event(UserEvent::SetTitle(t)); }
    pub fn set_size(&self, w: i32, h: i32, hints: u32) { let _ = self.proxy.send_event(UserEvent::SetSize(w, h, hints)); }
    pub fn set_bounds(&self, x: i32, y: i32, w: i32, h: i32) { let _ = self.proxy.send_event(UserEvent::SetBounds(x, y, w, h)); }
    pub fn navigate(&self, u: String) { let _ = self.proxy.send_event(UserEvent::Navigate(u)); }
    pub fn open_devtools(&self) { let _ = self.proxy.send_event(UserEvent::OpenDevtools); }
    pub fn eval(&self, j: String) { let _ = self.proxy.send_event(UserEvent::Eval(j)); }
    pub fn bind(&self, n: String, f: PyObject) { 
        if let Ok(mut cbs) = self.callbacks.lock() {
            Python::with_gil(|py| { cbs.insert(n.clone(), f.clone_ref(py)); });
        }
        let _ = self.proxy.send_event(UserEvent::Bind(n, f)); 
    }
    pub fn return_result(&self, s: String, st: i32, r: String) { let _ = self.proxy.send_event(UserEvent::Return(s, st, r)); }
    pub fn terminate(&self) { let _ = self.proxy.send_event(UserEvent::Quit); }
    pub fn show(&self) { let _ = self.proxy.send_event(UserEvent::SetVisible(true)); }
    pub fn hide(&self) { let _ = self.proxy.send_event(UserEvent::SetVisible(false)); }
    pub fn minimize(&self) { let _ = self.proxy.send_event(UserEvent::Minimize); }
    pub fn maximize(&self) { let _ = self.proxy.send_event(UserEvent::SetMaximized(true)); }
    pub fn unmaximize(&self) { let _ = self.proxy.send_event(UserEvent::SetMaximized(false)); }
    pub fn start_drag(&self) { let _ = self.proxy.send_event(UserEvent::DragWindow); }
    pub fn set_taskbar_progress(&self, s: i32, v: i32, m: i32) { let _ = self.proxy.send_event(UserEvent::TaskbarProgress(s, v, m)); }
    pub fn get_hwnd(&self) -> usize { self.hwnd }
    
    pub fn set_fullscreen(&self, e: bool) { let _ = self.proxy.send_event(UserEvent::SetFullscreen(e)); }
    pub fn set_always_on_top(&self, e: bool) { let _ = self.proxy.send_event(UserEvent::SetAlwaysOnTop(e)); }
    pub fn set_resizable(&self, e: bool) { let _ = self.proxy.send_event(UserEvent::SetResizable(e)); }
    pub fn set_decorations(&self, e: bool) { let _ = self.proxy.send_event(UserEvent::SetDecorations(e)); }
    pub fn center(&self) { let _ = self.proxy.send_event(UserEvent::CenterWindow); }

    pub fn set_prevent_close(&self, p: bool) {
        let _ = self.proxy.send_event(UserEvent::SetPreventClose(p));
    }
    
    pub fn set_is_utility(&self, u: bool) {
        *self.is_utility.lock().unwrap() = u;
    }
}
