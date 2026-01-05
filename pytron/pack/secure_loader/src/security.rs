use std::env;
use std::fs;
use std::io::{Read, Seek, SeekFrom};
use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce
};
// use rfd::{MessageButtons, MessageLevel, MessageDialog};

#[cfg(windows)]
extern crate winapi;

use crate::ui::alert;

pub fn check_debugger() {
    #[cfg(windows)]
    unsafe {
        // Multi-layered check: IsDebuggerPresent + Timing check
        if winapi::um::debugapi::IsDebuggerPresent() != 0 {
            alert("Security Alert", "Process integrity check failed (D1).");
            std::process::exit(0xDEAD);
        }
        
        // Simple timing check (debuggers slow down execution)
        let start = std::time::Instant::now();
        let mut _x = 0;
        for i in 0..1000 { _x += i; }
        if start.elapsed().as_micros() > 500 { // Way too slow for a simple loop
             // Optional: alert or just exit
        }
    }
}

// Footer format:
// [ KEY (32 bytes) ]
// [ MAGIC (8 bytes) "PYTRON_K" ]

pub fn get_footer_data() -> Result<[u8; 32], String> {
    let exe_path = env::current_exe().map_err(|e| format!("Failed to get EXE path: {}", e))?;
    let mut file = fs::File::open(&exe_path).map_err(|e| format!("Failed to open EXE: {}", e))?;
    
    // Read Fixed Footer (Key + Magic) = 32 + 8 = 40 bytes
    if file.seek(SeekFrom::End(-40)).is_err() {
        return Err("Binary too small or footer missing".to_string());
    }

    let mut footer = [0u8; 40];
    file.read_exact(&mut footer).map_err(|e| format!("Failed to read footer: {}", e))?;

    // layout: [key (0..32)] [magic (32..40)]
    let key_slice = &footer[0..32];
    let magic = &footer[32..40];

    if magic != b"PYTRON_K" {
        return Err("Security Footer Missing: Binary was not sealed.".to_string());
    }

    let mut key_arr = [0u8; 32];
    key_arr.copy_from_slice(key_slice);

    Ok(key_arr)
}

pub fn decrypt_payload(encrypted_data: &[u8]) -> Result<String, String> {
    if encrypted_data.len() < 12 {
        return Err("Payload too short".to_string());
    }

    let nonce_bytes = &encrypted_data[..12];
    let ciphertext = &encrypted_data[12..];

    // Get key from footer
    let key_bytes = get_footer_data().map_err(|e| format!("Key Access Error: {}", e))?;
    let cipher = Aes256Gcm::new((&key_bytes).into());
    let nonce = Nonce::from_slice(nonce_bytes);

    let decrypted = cipher.decrypt(nonce, ciphertext)
        .map_err(|e| format!("Decryption failed: {}", e))?;

    String::from_utf8(decrypted).map_err(|e| format!("Invalid UTF-8: {}", e))
}
