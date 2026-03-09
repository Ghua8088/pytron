use pyo3::prelude::*;
use libservo::{
    ServoBuilder, WebViewBuilder, WindowRenderingContext, WebView, WebViewDelegate,
    embedder_traits::EventLoopWaker,
};
use std::sync::{Arc, Mutex};
use std::rc::Rc;
use winit::{
    event::{Event, WindowEvent},
    event_loop::{ControlFlow, EventLoopBuilder, EventLoopProxy, EventLoopWindowTarget},
    window::WindowBuilder,
    raw_window_handle::{HasDisplayHandle, HasWindowHandle},
};
use std::num::NonZeroU32;
use url::Url;

extern crate gl;

#[derive(Debug)]
enum UserEvent {
    Show,
    Hide,
    Minimize,
    Maximize,
    Restore,
    SetTitle(String),
    Navigate(String),
    Close,
    Wake,
}

#[derive(Clone)]
struct Waker(winit::event_loop::EventLoopProxy<UserEvent>);

impl EventLoopWaker for Waker {
    fn clone_box(&self) -> Box<dyn EventLoopWaker> {
        Box::new(Self(self.0.clone()))
    }

    fn wake(&self) {
        if let Err(e) = self.0.send_event(UserEvent::Wake) {
            println!("[Servo-Pyd] Failed to wake: {:?}", e);
        }
    }
}

struct AppState {
    window: Arc<winit::window::Window>,
}

impl WebViewDelegate for AppState {
    fn notify_new_frame_ready(&self, _: WebView) {
        self.window.request_redraw();
    }
}

#[pyclass]
struct ServoEngine {
    proxy: Arc<Mutex<Option<EventLoopProxy<UserEvent>>>>,
}

#[pymethods]
impl ServoEngine {
    #[new]
    fn new() -> Self {
        ServoEngine {
            proxy: Arc::new(Mutex::new(None)),
        }
    }

    fn run(&self, title: String, width: u32, height: u32) -> PyResult<()> {
        let event_loop = EventLoopBuilder::<UserEvent>::with_user_event().build().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create event loop: {}", e))
        })?;

        let window = WindowBuilder::new()
            .with_title(title)
            .with_inner_size(winit::dpi::LogicalSize::new(width, height))
            .with_maximized(true) // Ensure it fills screen better
            .with_visible(true)
            .build(&event_loop)
            .map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create window: {}", e))
            })?;

        let window = Arc::new(window);
        
        let context = softbuffer::Context::new(window.clone()).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create softbuffer context: {}", e))
        })?;
        let mut surface = softbuffer::Surface::new(&context, window.clone()).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create softbuffer surface: {}", e))
        })?;

        // Store the proxy so methods like show() can wake up the loop
        {
            let mut p = self.proxy.lock().unwrap();
            *p = Some(event_loop.create_proxy());
        }

        // Initial Redraw Request
        window.request_redraw();

        println!("[Servo-Pyd] Starting Native Event Loop...");
        println!("[Servo-Pyd] Note: Binary will be large once Servo is linked.");
        
        // This links the entire Servo engine into our DLL
        let _ = std::mem::size_of::<libservo::Servo>();

        event_loop.run(move |event: Event<UserEvent>, elwt: &EventLoopWindowTarget<UserEvent>| {
            elwt.set_control_flow(ControlFlow::Wait);

            match event {
                Event::UserEvent(user_event) => match user_event {
                    UserEvent::Show => window.set_visible(true),
                    UserEvent::Hide => window.set_visible(false),
                    UserEvent::Minimize => window.set_minimized(true),
                    UserEvent::Maximize => window.set_maximized(true),
                    UserEvent::Restore => {
                        let _ = window.set_maximized(false);
                        window.set_minimized(false);
                    }
                    UserEvent::SetTitle(t) => window.set_title(&t),
                    UserEvent::Navigate(url) => {
                        println!("[Servo-Pyd] Navigation Requested: {}", url);
                        // TODO: Translate to Servo Webview APIs
                    }
                    UserEvent::Close => elwt.exit(),
                },
                Event::WindowEvent {
                    event: WindowEvent::Resized(physical_size),
                    window_id,
                } if window_id == window.id() => {
                    println!("[Servo-Pyd] Resizing Viewport: {}x{}", physical_size.width, physical_size.height);
                    if let (Some(w), Some(h)) = (NonZeroU32::new(physical_size.width), NonZeroU32::new(physical_size.height)) {
                        surface.resize(w, h).unwrap();
                    }
                    window.request_redraw();
                },
                Event::WindowEvent {
                    event: WindowEvent::RedrawRequested,
                    window_id,
                } if window_id == window.id() => {
                    let mut buffer = surface.buffer_mut().unwrap();
                    for pixel in buffer.iter_mut() {
                        *pixel = 0xFFFFFFFF; // White
                    }
                    buffer.present().unwrap();
                },
                Event::WindowEvent {
                    event: WindowEvent::CloseRequested,
                    ..
                } => elwt.exit(),
                _ => (),
            }
        }).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Event loop error: {}", e))
        })
    }

    fn show(&self) -> PyResult<()> {
        self.send_event(UserEvent::Show)
    }

    fn hide(&self) -> PyResult<()> {
        self.send_event(UserEvent::Hide)
    }

    fn set_title(&self, title: String) -> PyResult<()> {
        self.send_event(UserEvent::SetTitle(title))
    }

    fn navigate(&self, url: String) -> PyResult<()> {
        self.send_event(UserEvent::Navigate(url))
    }

    fn close(&self) -> PyResult<()> {
        self.send_event(UserEvent::Close)
    }
}

impl ServoEngine {
    fn send_event(&self, event: UserEvent) -> PyResult<()> {
        let proxy_lock = self.proxy.lock().unwrap();
        if let Some(proxy) = proxy_lock.as_ref() {
            proxy.send_event(event).map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to send event: {}", e))
            })?;
        }
        Ok(())
    }
}

#[pymodule]
fn pytron_servo(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ServoEngine>()?;
    Ok(())
}
