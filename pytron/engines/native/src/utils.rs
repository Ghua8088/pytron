use std::panic;

pub fn setup_panic_hook() {
    static ONCE: std::sync::Once = std::sync::Once::new();
    ONCE.call_once(|| {
        panic::set_hook(Box::new(|info| {
            let location = info.location().map(|l| format!("{}:{}:{}", l.file(), l.line(), l.column())).unwrap_or_else(|| "unknown".to_string());
            let msg = match info.payload().downcast_ref::<&str>() {
                Some(s) => *s,
                None => match info.payload().downcast_ref::<String>() {
                    Some(s) => &s[..],
                    None => "Box<Any>",
                },
            };
            eprintln!("[PYTRON PANIC] Fatal Error at {}: {}", location, msg);
        }));
    });
}

pub struct SendWrapper<T>(pub T);
unsafe impl<T> Send for SendWrapper<T> {}
unsafe impl<T> Sync for SendWrapper<T> {}

impl<T> SendWrapper<T> {
    pub fn new(val: T) -> Self { Self(val) }
    pub fn take(self) -> T { self.0 }
}

impl<T: Clone> Clone for SendWrapper<T> {
    fn clone(&self) -> Self {
        Self(self.0.clone())
    }
}

// load_icon removed — icon loading for tray is now owned by pytron_os
