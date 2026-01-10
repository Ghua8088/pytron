use std::env;
use std::fs;
use std::io::{Read, Seek, SeekFrom};
use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce
};
use obfstr::obfstr;

#[cfg(windows)]
extern crate winapi;

use crate::ui::alert;

pub fn check_debugger() {
    #[cfg(windows)]
    unsafe {
        // 1. Standard Check
        if winapi::um::debugapi::IsDebuggerPresent() != 0 {
            alert(obfstr!("Security Alert"), obfstr!("Process integrity check failed (D1)."));
            std::process::exit(0xDEAD);
        }

        // 2. Remote Debugger Check
        let mut is_remote_debugger_present = 0;
        winapi::um::debugapi::CheckRemoteDebuggerPresent(
            winapi::um::processthreadsapi::GetCurrentProcess(),
            &mut is_remote_debugger_present,
        );
        if is_remote_debugger_present != 0 {
            alert(obfstr!("Security Alert"), obfstr!("Unauthorized debugger detected (D2)."));
            std::process::exit(0xDEAB);
        }
        
        // 3. Timing check (debuggers slow down execution)
        let start = std::time::Instant::now();
        let mut x = 0;
        for i in 0..10_000 { 
            x = std::hint::black_box(x + i); 
        }
        // If it takes more than 5ms for a simple loop, something is wrong
        if start.elapsed().as_millis() > 5 {
             alert(obfstr!("Security Alert"), obfstr!("Timing anomaly detected. Binary compromised."));
             std::process::exit(0xDEAC);
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
        return Err(obfstr!("Binary too small or footer missing").to_string());
    }

    let mut footer = [0u8; 40];
    file.read_exact(&mut footer).map_err(|e| format!("Failed to read footer: {}", e))?;

    // layout: [key (0..32)] [magic (32..40)]
    let key_slice = &footer[0..32];
    let magic = &footer[32..40];

    if magic != b"PYTRON_K" {
        return Err(obfstr!("Security Footer Missing: Binary was not sealed.").to_string());
    }

    let mut key_arr = [0u8; 32];
    key_arr.copy_from_slice(key_slice);

    Ok(key_arr)
}

pub fn decrypt_payload(encrypted_data: &[u8]) -> Result<Vec<u8>, String> {
    if encrypted_data.len() < 12 {
        return Err(obfstr!("Payload too short").to_string());
    }

    let nonce_bytes = &encrypted_data[..12];
    let ciphertext = &encrypted_data[12..];

    // Get key from footer
    let key_bytes = get_footer_data().map_err(|e| format!("Key Access Error: {}", e))?;
    let cipher = Aes256Gcm::new((&key_bytes).into());
    let nonce = Nonce::from_slice(nonce_bytes);

    cipher.decrypt(nonce, ciphertext)
        .map_err(|e| format!("Decryption failed: {}", e))
}
