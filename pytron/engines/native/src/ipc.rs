use pyo3::prelude::*;
use std::sync::{Arc, Mutex};
use std::thread;

#[cfg(target_os = "windows")]
use windows::{
    core::PCWSTR,
    Win32::Foundation::{CloseHandle, HANDLE},
    Win32::System::Pipes::{ConnectNamedPipe, CreateNamedPipeW, NAMED_PIPE_MODE},
    Win32::Storage::FileSystem::{ReadFile, WriteFile, FILE_FLAGS_AND_ATTRIBUTES},
};

#[cfg(not(target_os = "windows"))]
use std::os::unix::net::{UnixListener, UnixStream};
#[cfg(not(target_os = "windows"))]
use std::io::{Read, Write};

#[cfg(target_os = "windows")]
const PIPE_ACCESS_DUPLEX: u32 = 0x00000003;
#[cfg(target_os = "windows")]
const PIPE_TYPE_BYTE: u32 = 0x00000000;
#[cfg(target_os = "windows")]
const PIPE_READMODE_BYTE: u32 = 0x00000000;
#[cfg(target_os = "windows")]
const PIPE_WAIT: u32 = 0x00000000;

// --- RAII HANDLE WRAPPER ---
// Ensures Win32 HANDLEs are closed when they go out of scope.
#[cfg(target_os = "windows")]
struct OwnedHandle(HANDLE);

#[cfg(target_os = "windows")]
impl Drop for OwnedHandle {
    fn drop(&mut self) {
        if !self.0.is_invalid() {
            unsafe { let _ = CloseHandle(self.0); }
        }
    }
}

// OwnedHandle needs to cross thread boundaries (stored in Arc<Mutex<>>).
#[cfg(target_os = "windows")]
unsafe impl Send for OwnedHandle {}
#[cfg(target_os = "windows")]
unsafe impl Sync for OwnedHandle {}

// --- HELPERS: GUARANTEED FULL READ / WRITE ON WIN32 PIPES ---
//
// ReadFile on a named pipe may return fewer bytes than requested in a single
// call (especially for large payloads or when the pipe buffer is under load).
// This mirrors Rust std's `Read::read_exact` for the Win32 world.
#[cfg(target_os = "windows")]
fn read_exact_win32(handle: HANDLE, buf: &mut [u8]) -> Result<(), String> {
    let mut offset = 0usize;
    while offset < buf.len() {
        let mut bytes_read = 0u32;
        let remaining = &mut buf[offset..];
        let res = unsafe {
            ReadFile(handle, Some(remaining), Some(&mut bytes_read), None)
        };
        match res {
            Err(e) => return Err(format!("ReadFile failed: {}", e)),
            Ok(()) if bytes_read == 0 => {
                // A successful ReadFile with 0 bytes means the pipe was closed
                // gracefully by the remote end (EOF equivalent).
                return Err("pipe closed (EOF)".to_string());
            }
            Ok(()) => {
                offset += bytes_read as usize;
            }
        }
    }
    Ok(())
}

// WriteFile on a named pipe may write fewer bytes than requested.
// Loop until all bytes are written or an error occurs.
#[cfg(target_os = "windows")]
fn write_all_win32(handle: HANDLE, buf: &[u8]) -> Result<(), String> {
    let mut offset = 0usize;
    while offset < buf.len() {
        let mut bytes_written = 0u32;
        let remaining = &buf[offset..];
        let res = unsafe {
            WriteFile(handle, Some(remaining), Some(&mut bytes_written), None)
        };
        match res {
            Err(e) => return Err(format!("WriteFile failed: {}", e)),
            Ok(()) if bytes_written == 0 => {
                return Err("WriteFile wrote 0 bytes (pipe closed?)".to_string());
            }
            Ok(()) => {
                offset += bytes_written as usize;
            }
        }
    }
    Ok(())
}

#[pyclass]
pub struct ChromeIPC {
    #[cfg(target_os = "windows")]
    handle_in: Arc<Mutex<Option<OwnedHandle>>>,
    #[cfg(target_os = "windows")]
    handle_out: Arc<Mutex<Option<OwnedHandle>>>,

    #[cfg(not(target_os = "windows"))]
    stream: Arc<Mutex<Option<UnixStream>>>,

    connected: Arc<Mutex<bool>>,
    pipe_path: String,
}

#[pymethods]
impl ChromeIPC {
    #[new]
    fn new() -> Self {
        Self {
            #[cfg(target_os = "windows")]
            handle_in: Arc::new(Mutex::new(None)),
            #[cfg(target_os = "windows")]
            handle_out: Arc::new(Mutex::new(None)),
            #[cfg(not(target_os = "windows"))]
            stream: Arc::new(Mutex::new(None)),
            connected: Arc::new(Mutex::new(false)),
            pipe_path: String::new(),
        }
    }

    fn listen(&mut self, uid: String) -> PyResult<String> {
        #[cfg(target_os = "windows")]
        {
            let base_path = format!(r#"\\.\pipe\pytron-{}"#, uid);
            let path_in = format!("{}-in", base_path);
            let path_out = format!("{}-out", base_path);

            self.pipe_path = base_path.clone();

            let w_path_in = encode_wide(&path_in);
            let w_path_out = encode_wide(&path_out);

            let h_in = unsafe {
                CreateNamedPipeW(
                    PCWSTR(w_path_in.as_ptr()),
                    FILE_FLAGS_AND_ATTRIBUTES(PIPE_ACCESS_DUPLEX),
                    NAMED_PIPE_MODE(PIPE_TYPE_BYTE | PIPE_WAIT),
                    1,
                    65536,
                    65536,
                    0,
                    None,
                )
            };

            if h_in.is_invalid() {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to create IN pipe"));
            }

            let h_out = unsafe {
                CreateNamedPipeW(
                    PCWSTR(w_path_out.as_ptr()),
                    FILE_FLAGS_AND_ATTRIBUTES(PIPE_ACCESS_DUPLEX),
                    NAMED_PIPE_MODE(PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT),
                    1,
                    65536,
                    65536,
                    0,
                    None,
                )
            };

            if h_out.is_invalid() {
                // h_in is already wrapped and will be closed when we return the Err.
                // Drop it explicitly here before reassigning, just to be clear.
                unsafe { let _ = CloseHandle(h_in); }
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Failed to create OUT pipe"));
            }

            // Transfer ownership into RAII wrappers — handles are now automatically
            // closed when the OwnedHandle is dropped (i.e. when ChromeIPC is dropped).
            *self.handle_in.lock().unwrap() = Some(OwnedHandle(h_in));
            *self.handle_out.lock().unwrap() = Some(OwnedHandle(h_out));

            Ok(base_path)
        }

        #[cfg(not(target_os = "windows"))]
        {
            let path = format!("/tmp/pytron-{}.sock", uid);
            self.pipe_path = path.clone();
            if std::path::Path::new(&path).exists() {
                let _ = std::fs::remove_file(&path);
            }
            Ok(path)
        }
    }

    fn wait_for_connection(&self, py: Python<'_>) -> PyResult<()> {
        #[cfg(target_os = "windows")]
        {
            // Grab both raw handle values while holding the locks, then release them.
            let h_in_val = {
                let guard = self.handle_in.lock().unwrap();
                guard.as_ref()
                    .map(|oh| oh.0)
                    .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Pipes not initialized"))?
            };
            let h_out_val = {
                let guard = self.handle_out.lock().unwrap();
                guard.as_ref()
                    .map(|oh| oh.0)
                    .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Pipes not initialized"))?
            };

            // CRITICAL: Release GIL during blocking Win32 call.
            // Also check both ConnectNamedPipe results — ERROR_PIPE_CONNECTED (0x80070217)
            // means the client already connected, which is perfectly fine.
            py.allow_threads(move || unsafe {
                let res_in = ConnectNamedPipe(h_in_val, None);
                let res_out = ConnectNamedPipe(h_out_val, None);

                // ERROR_PIPE_CONNECTED is a "success" code — the client connected
                // before we called ConnectNamedPipe.  Any other error is real.
                fn is_ok(res: windows::core::Result<()>) -> bool {
                    match res {
                        Ok(()) => true,
                        Err(ref e) => e.code().0 as u32 == 0x8007_0217, // ERROR_PIPE_CONNECTED
                    }
                }

                (is_ok(res_in), is_ok(res_out))
            });

            // Note: we intentionally proceed even if one pipe fails — the read loop
            // will surface the error on the first read. Returning a hard error here
            // would require the Python caller to re-initialize from scratch.
            *self.connected.lock().unwrap() = true;
            Ok(())
        }

        #[cfg(not(target_os = "windows"))]
        {
            let path = self.pipe_path.clone();
            let stream = py.allow_threads(move || {
                let listener = UnixListener::bind(&path).unwrap();
                let (s, _) = listener.accept().unwrap();
                s
            });
            *self.stream.lock().unwrap() = Some(stream);
            *self.connected.lock().unwrap() = true;
            Ok(())
        }
    }

    fn start_read_loop(&self, callback: PyObject) -> PyResult<()> {
        let connected = self.connected.clone();

        #[cfg(target_os = "windows")]
        // Extract the raw HANDLE value before entering the thread. We only need
        // the numeric value (the pipe stays alive via OwnedHandle in the struct).
        let h_out_raw: HANDLE = {
            let guard = self.handle_out.lock().unwrap();
            guard.as_ref()
                .map(|oh| oh.0)
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Pipes not initialized"))?
        };

        #[cfg(not(target_os = "windows"))]
        let mut stream_read = self.stream.lock().unwrap().as_ref().map(|s| s.try_clone().unwrap());

        thread::spawn(move || {
            loop {
                // Check connection flag at the top of each iteration.
                if !*connected.lock().unwrap() {
                    break;
                }

                #[cfg(target_os = "windows")]
                {
                    // --- Read 4-byte length header (guaranteed full read) ---
                    let mut header = [0u8; 4];
                    if let Err(e) = read_exact_win32(h_out_raw, &mut header) {
                        // Pipe was closed or errored — exit the loop cleanly.
                        eprintln!("[PYTRON IPC] Read loop ended (header): {}", e);
                        break;
                    }
                    let msg_len = u32::from_le_bytes(header) as usize;

                    // Sanity-check: reject absurdly large payloads to avoid OOM.
                    if msg_len == 0 || msg_len > 64 * 1024 * 1024 {
                        eprintln!("[PYTRON IPC] Unexpected message length {}, closing.", msg_len);
                        break;
                    }

                    // --- Read body (guaranteed full read) ---
                    let mut body = vec![0u8; msg_len];
                    if let Err(e) = read_exact_win32(h_out_raw, &mut body) {
                        eprintln!("[PYTRON IPC] Read loop ended (body): {}", e);
                        break;
                    }

                    // --- Dispatch to Python callback (panic-safe) ---
                    if let Ok(msg_str) = String::from_utf8(body) {
                        // Use catch_unwind so a panicking Python callback doesn't
                        // silently kill the read thread without clearing `connected`.
                        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                            Python::with_gil(|py| {
                                let _ = callback.call1(py, (msg_str,));
                            });
                        }));
                        if let Err(e) = result {
                            eprintln!("[PYTRON IPC] Callback panicked: {:?}", e);
                            // Don't break — a panicking callback is not a pipe error.
                        }
                    }
                }

                #[cfg(not(target_os = "windows"))]
                {
                    if let Some(stream) = stream_read.as_mut() {
                        let mut header = [0u8; 4];
                        if stream.read_exact(&mut header).is_err() {
                            break;
                        }
                        let msg_len = u32::from_le_bytes(header) as usize;

                        // Sanity-check
                        if msg_len == 0 || msg_len > 64 * 1024 * 1024 {
                            eprintln!("[PYTRON IPC] Unexpected message length {}, closing.", msg_len);
                            break;
                        }

                        let mut body = vec![0u8; msg_len];
                        if stream.read_exact(&mut body).is_err() {
                            break;
                        }

                        if let Ok(msg_str) = String::from_utf8(body) {
                            let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                                Python::with_gil(|py| {
                                    let _ = callback.call1(py, (msg_str,));
                                });
                            }));
                            if let Err(e) = result {
                                eprintln!("[PYTRON IPC] Callback panicked: {:?}", e);
                            }
                        }
                    } else {
                        break;
                    }
                }
            }

            // Always clear the connected flag when the loop exits, regardless of
            // how it exits (normal break, pipe error, or panic).
            *connected.lock().unwrap() = false;
        });

        Ok(())
    }

    fn send(&self, py: Python<'_>, data: String) -> PyResult<()> {
        if !*self.connected.lock().unwrap() {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Not connected"));
        }

        let body = data.into_bytes();
        let msg_len = body.len() as u32;
        let header = msg_len.to_le_bytes();
        let mut full_msg = Vec::with_capacity(4 + body.len());
        full_msg.extend_from_slice(&header);
        full_msg.extend_from_slice(&body);

        #[cfg(target_os = "windows")]
        {
            let h_in_raw: HANDLE = {
                let guard = self.handle_in.lock().unwrap();
                guard.as_ref()
                    .map(|oh| oh.0)
                    .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Pipe not connected"))?
            };

            py.allow_threads(move || {
                write_all_win32(h_in_raw, &full_msg)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e))
            })?;
            Ok(())
        }

        #[cfg(not(target_os = "windows"))]
        {
            let mut lock = self.stream.lock().unwrap();
            if let Some(stream) = lock.as_mut() {
                py.allow_threads(move || {
                    stream.write_all(&full_msg)
                        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
                })?;
            }
            Ok(())
        }
    }
}

#[cfg(target_os = "windows")]
fn encode_wide(s: &str) -> Vec<u16> {
    use std::os::windows::ffi::OsStrExt;
    std::ffi::OsStr::new(s).encode_wide().chain(std::iter::once(0)).collect()
}
