use std::borrow::Cow;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::collections::HashMap;
use pyo3::prelude::*;
use wry::http::{Response, header, StatusCode, Method, Request};

fn inject_bridge(data: Vec<u8>, callbacks: Arc<Mutex<HashMap<String, PyObject>>>) -> Vec<u8> {
    if let Ok(content) = String::from_utf8(data.clone()) {
        let mut method_bindings = String::new();
        if let Ok(cbs) = callbacks.lock() {
            for name in cbs.keys() {
                method_bindings.push_str(&format!(
                    "window['{}'] = (...args) => window.__pytron_native_bridge('{}', args);\n",
                    name, name
                ));
            }
        }

        let bridge_script = format!(r#"
        <script>
        window.pytron_is_native = true;
        window.pytron = window.pytron || {{}};
        window.pytron.is_ready = true;
        window.__pytron_native_bridge = (method, args) => {{
            const seq = Math.random().toString(36).substring(2, 10);
            const ipc = window.ipc || window.chrome?.webview || window.webkit?.messageHandlers?.ipc;
            if (ipc) {{
                ipc.postMessage(JSON.stringify({{id: seq, method: method, params: args}}));
            }} else {{
                console.error("Pytron IPC not initialized.");
            }}
            return new Promise((resolve, reject) => {{
                window._rpc = window._rpc || {{}};
                window._rpc[seq] = {{resolve, reject}};
            }});
        }};

        // Dynamic Proxy for window.pytron.* calls
        window.pytron = new Proxy(window.pytron, {{
            get: (target, prop) => {{
                if (prop in target) return target[prop];
                return (...args) => window.__pytron_native_bridge(prop, args);
            }}
        }});

        window.pytron_close = () => window.__pytron_native_bridge('pytron_close', []);
        window.pytron_drag = () => window.__pytron_native_bridge('pytron_drag', []);
        window.pytron_log = (msg) => window.__pytron_native_bridge('pytron_log', [msg]);
        
        // Override alert to use native message box
        window.alert = (msg) => {{
            window.__pytron_native_bridge('pytron_message_box', ["Alert", String(msg), "info"]);
        }};
        {}
        </script>
        "#, method_bindings);

        let injected = if content.contains("</head>") {
            content.replace("</head>", &format!("{}</head>", bridge_script))
        } else if content.contains("<body>") {
            content.replace("<body>", &format!("<body>{}", bridge_script))
        } else {
            format!("{}{}", bridge_script, content)
        };
        return injected.into_bytes();
    }
    data
}

pub fn handle_pytron_protocol(
    request: Request<Vec<u8>>,
    protocol_root: PathBuf,
    callbacks: Arc<Mutex<HashMap<String, PyObject>>>,
) -> Response<Cow<'static, [u8]>> {
    let uri = request.uri();
    let method = request.method();
    
    // 1. Handle CORS Preflight
    if method == Method::OPTIONS {
        return Response::builder()
            .header("Access-Control-Allow-Origin", "*")
            .header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            .header("Access-Control-Allow-Headers", "*")
            .body(Cow::from(Vec::new())).unwrap();
    }

    // 2. Extract the path correctly
    // We look for "app/" or "/app/" in the URI to find where our virtual files start.
    let full_uri = uri.to_string();
    
    let clean_path = if let Some(pos) = full_uri.find("/app/") {
        &full_uri[pos + 5..]
    } else if let Some(pos) = full_uri.find("app/") {
        // Fallback for cases where it might not have leading slash in some parsers
        &full_uri[pos + 4..]
    } else {
        // If app/ not found, fallback to just the path part
        uri.path().trim_start_matches('/')
    };
    
    // Remove query strings or fragments if they leaked into clean_path
    let clean_path = clean_path.split('?').next().unwrap_or(clean_path);
    let clean_path = clean_path.split('#').next().unwrap_or(clean_path);

    if clean_path == "about:blank" || clean_path.is_empty() {
         return Response::builder()
            .status(StatusCode::OK)
            .body(Cow::from(Vec::new()))
            .unwrap();
    }

    let decoded = urlencoding::decode(clean_path).unwrap_or(Cow::Borrowed(clean_path));
    
    // SECURITY: Path Traversal Mitigation
    // Reject paths with '..' or absolute roots to prevent escaping protocol_root
    if decoded.contains("..") || decoded.starts_with('/') || decoded.contains(':') || decoded.starts_with('\\') {
         return Response::builder().status(StatusCode::FORBIDDEN).body(Cow::from(Vec::new())).unwrap();
    }

    // --- VAP FIRST STRATEGY ---
    // We check Python-served memory assets BEFORE checking the disk.
    // This allows bundling all UI into an uneditable .pytron archive while loose files are ignored.
    let mut served_data: Option<(Vec<u8>, String)> = None;
    let func_opt = {
        if let Ok(cbs) = callbacks.lock() {
             cbs.get("pytron_serve_asset").map(|f| Python::with_gil(|py| f.clone_ref(py)))
        } else {
            None
        }
    };

    if let Some(func) = func_opt {
         Python::with_gil(|py| {
             if let Ok(res) = func.call1(py, (decoded.as_ref(),)) {
                 if let Ok((data, mime)) = res.extract::<(Vec<u8>, String)>(py) {
                     served_data = Some((data, mime));
                 }
             }
         });
    }

    if let Some((data, mime)) = served_data {
         let mut resp_data = data;
         if mime.contains("html") {
             resp_data = inject_bridge(resp_data, callbacks.clone());
         }

         return Response::builder()
            .status(StatusCode::OK)
            .header(header::CONTENT_TYPE, mime)
            .header("Access-Control-Allow-Origin", "*")
            .body(Cow::from(resp_data))
            .unwrap();
    }

    // --- DISK FALLBACK ---
    let mut final_path = protocol_root.join(decoded.as_ref());
    if final_path.is_dir() {
        final_path = final_path.join("index.html");
    }

    match std::fs::read(&final_path) {
        Ok(data) => {
            let mime = mime_guess::from_path(&final_path).first_or_octet_stream();
            let mime_str = mime.to_string();
            let mut resp_data = data;

            if mime.subtype() == "html" {
                resp_data = inject_bridge(resp_data, callbacks.clone());
            }

            Response::builder()
                .status(StatusCode::OK)
                .header(header::CONTENT_TYPE, mime_str)
                .header("Access-Control-Allow-Origin", "*")
                .body(Cow::from(resp_data))
                .unwrap()
        }
        Err(_) => {
            Response::builder().status(StatusCode::NOT_FOUND).body(Cow::from(Vec::new())).unwrap()
        }
    }
}

// -------------------------------------------------------------------
// Unit Tests
// -------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_path_traversal_mitigation() {
        // We simulate how handle_pytron_protocol parses paths
        let cases = vec![
            ("sub/file.js", false),
            ("../file.js", true),
            ("a/../../etc/passwd", true),
            ("C:/Windows/System32", true),
            ("/absolute/path", true),
            ("\\\\network\\share", true),
        ];

        for (path, should_fail) in cases {
            let decoded = urlencoding::decode(path).unwrap();
            let is_insecure = decoded.contains("..") || decoded.starts_with('/') || decoded.contains(':') || decoded.starts_with('\\');
            assert_eq!(is_insecure, should_fail, "Path security failed for: {}", path);
        }
    }

    #[test]
    fn test_inject_bridge_html_structure() {
        // Mock callbacks
        let cbs = Arc::new(Mutex::new(HashMap::new()));
        
        let html_with_head = b"<html><head><title>Test</title></head><body></body></html>".to_vec();
        let result = inject_bridge(html_with_head, cbs.clone());
        let result_str = String::from_utf8(result).unwrap();
        assert!(result_str.contains("window.pytron_is_native = true;"));
        assert!(result_str.contains("</head>"));
        // Script should be BEFORE head closing
        assert!(result_str.find("window.pytron_is_native").unwrap() < result_str.find("</head>").unwrap());

        let html_no_head = b"<html><body>Hello</body></html>".to_vec();
        let result = inject_bridge(html_no_head, cbs.clone());
        let result_str = String::from_utf8(result).unwrap();
        assert!(result_str.contains("window.pytron_is_native = true;"));
        assert!(result_str.contains("<body>"));

        let raw_text = b"Just some text".to_vec();
        let result = inject_bridge(raw_text, cbs);
        let result_str = String::from_utf8(result).unwrap();
        assert!(result_str.contains("window.pytron_is_native = true;"));
        assert!(result_str.contains("Just some text"));
    }
}
