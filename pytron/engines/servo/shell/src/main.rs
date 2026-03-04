use byteorder::{LittleEndian, ReadBytesExt, WriteBytesExt};
use clap::Parser;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs::File;
use std::io::{Read, Write};
use std::thread;

// Servo specific imports
use servo::Servo;
use url::Url;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(long = "pytron-pipe")]
    pytron_pipe: String,
    
    #[arg(long = "pytron-root")]
    pytron_root: String,
    
    #[arg(long)]
    inspect: bool,
}

#[derive(Serialize, Deserialize, Debug)]
struct IpcMessage {
    #[serde(rename = "type")]
    msg_type: String,
    payload: Value,
}

fn main() {
    let args = Args::parse();
    
    println!("[Servo-Shell] Starting Servo Web Engine...");
    println!("[Servo-Shell] Pipe: {}", args.pytron_pipe);
    println!("[Servo-Shell] Root: {}", args.pytron_root);

    #[cfg(target_os = "windows")]
    let (mut pipe_read, mut pipe_write) = connect_windows_pipes(&args.pytron_pipe);

    #[cfg(not(target_os = "windows"))]
    let (mut pipe_read, mut pipe_write) = connect_unix_socket(&args.pytron_pipe);

    // Send app_ready hand-shake
    let ready_msg = IpcMessage {
        msg_type: "lifecycle".to_string(),
        payload: Value::String("app_ready".to_string()),
    };
    send_msg(&mut pipe_write, &ready_msg);

    // TODO: Init Surfman, Winit, setup OpenGL context.
    // Initialize the actual Servo Engine instance:
    
    // Example:
    /*
    let opts = servo::config::opts::Opts { ... };
    servo::config::opts::set_defaults(opts);
    
    // We would need a WindowEmbedder and WindowCallbacks implementation here
    let mut servo_instance = Servo::new(
        Box::new(embedder),
        window,
        Url::parse("https://servo.org").unwrap()
    );
    */

    loop {
        match read_msg(&mut pipe_read) {
            Ok(msg) => {
                println!("[Servo-Shell] Received: {:?}", msg);
                
                // Parse commands like 'navigate', 'close', etc.
                if let Some(obj) = msg.as_object() {
                    if let Some(action) = obj.get("action").and_then(|v| v.as_str()) {
                        match action {
                            "navigate" => {
                                if let Some(url_str) = obj.get("url").and_then(|v| v.as_str()) {
                                    println!("[Servo-Shell] Navigating Servo to: {}", url_str);
                                    // servo_instance.handle_events(vec![...]);
                                }
                            }
                            "close" => {
                                println!("[Servo-Shell] Closing...");
                                break;
                            }
                            _ => {}
                        }
                    }
                }
            }
            Err(e) => {
                println!("[Servo-Shell] IPC Error or Disconnect: {:?}", e);
                break;
            }
        }
    }
}

fn send_msg<W: Write>(writer: &mut W, msg: &IpcMessage) {
    let json_bytes = serde_json::to_vec(msg).unwrap();
    writer.write_u32::<LittleEndian>(json_bytes.len() as u32).unwrap();
    writer.write_all(&json_bytes).unwrap();
    writer.flush().unwrap();
}

fn read_msg<R: Read>(reader: &mut R) -> std::io::Result<Value> {
    let len = reader.read_u32::<LittleEndian>()?;
    let mut buf = vec![0u8; len as usize];
    reader.read_exact(&mut buf)?;
    let v: Value = serde_json::from_slice(&buf)?;
    Ok(v)
}

#[cfg(target_os = "windows")]
fn connect_windows_pipes(base: &str) -> (File, File) {
    use std::time::Duration;
    let path_in = format!("{}-out", base); // we read from python's out
    let path_out = format!("{}-in", base); // we write to python's in
    
    let mut pipe_read = None;
    let mut pipe_write = None;
    
    while pipe_read.is_none() || pipe_write.is_none() {
        if pipe_read.is_none() {
            if let Ok(f) = File::open(&path_in) {
                pipe_read = Some(f);
            }
        }
        if pipe_write.is_none() {
            if let Ok(f) = std::fs::OpenOptions::new().write(true).open(&path_out) {
                pipe_write = Some(f);
            }
        }
        thread::sleep(Duration::from_millis(50));
    }
    
    (pipe_read.unwrap(), pipe_write.unwrap())
}

#[cfg(not(target_os = "windows"))]
fn connect_unix_socket(base: &str) -> (std::os::unix::net::UnixStream, std::os::unix::net::UnixStream) {
    use std::os::unix::net::UnixStream;
    use std::time::Duration;
    
    loop {
        if let Ok(stream) = UnixStream::connect(base) {
            return (stream.try_clone().unwrap(), stream);
        }
        thread::sleep(Duration::from_millis(50));
    }
}
