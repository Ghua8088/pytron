# Pytron VAP: Virtual Asset Provider

The **Virtual Asset Provider (VAP)** is a high-performance, zero-copy binary bridge designed specifically for Pytron. It allows the Python backend to serve large binary data (images, video frames, AI tensors, datasets) to the frontend with **near-zero overhead**.

## The Problem: The "Base64 Gap"
In traditional Electron or Webview frameworks, sending an image from Python to JavaScript usually involves:
1.  **Python**: Take binary -> Convert to Base64 string (~33% size increase).
2.  **Bridge**: Send massive JSON string over IPC.
3.  **JavaScript**: Parse JSON -> Create Data URI -> Browser decodes Base64 back to bits.

This process is slow, CPU-intensive, and doubles memory usage. For apps doing local AI (like Ollama or Stable Diffusion) or video processing, this is a massive bottleneck.

## The Solution: The `pytron://` Protocol
VAP introduces a virtual protocol handler. Instead of pushing data to JS, Python **serves** it on a high-speed internal bus, and JS **pulls** it only when needed.

### 1. Python: Serving Data
Use `window.serve_data(key, data, mime_type)    ` to put binary data into the VAP memory pool.

```python
# Serve a raw byte array as a JPEG
image_bytes = camera.capture() 
window.serve_data("stream-frame", image_bytes, "image/jpeg")

# Optional: Clean up when no longer needed
# window.unserve_data("stream-frame")
```

### 2. Frontend: Consuming Data
Pytron injects a sophisticated interceptor that handles `pytron://` URLs automatically.

#### Using HTML Tags
You can use the protocol directly in your UI. Pytron's `MutationObserver` will detect these and resolve them.
```html
<img src="pytron://stream-frame" />
```

#### Using `fetch()`
You can fetch raw binary data using the standard Web API. Pytron intercepts the request and returns a `Blob`.
```javascript
const response = await fetch('pytron://stream-frame');
const blob = await response.blob(); 
const url = URL.createObjectURL(blob);
```

---

## Under the Hood: How it Works (Technical)

Pytron uses a specialized "Hybrid Interception" technique to move binary data across the C-bridge without corruption or excessive encoding.

### The Latin-1 Serialization Trick
Standard JSON-based IPC cannot handle raw binary (it crashes on non-UTF-8 bytes). Pytron pipes the data through a **Latin-1 (ISO-8859-1)** mapping:
1.  **Backend**: The `bytes` object is decoded using `latin-1`. This maps every byte (0-255) to a single unicode character, preserving the exact bit pattern.
2.  **Bridge**: The "string" is sent over the bridge as a standard string.
3.  **Frontend**: The JS interceptor receives the string and reconstructs the bits:
    ```javascript
    const bytes = new Uint8Array(asset.raw.length);
    for (let i = 0; i < asset.raw.length; i++) {
        bytes[i] = asset.raw.charCodeAt(i);
    }
    const blob = new Blob([bytes], {type: asset.mime});
    ```

### The Mutation Observer
Because `webview` engines don't always support custom protocol registration at the system level (e.g., `WebView2`), Pytron uses a **DOM MutationObserver**. 
*   It watches every `<img>`, `<script>`, and `<link>` tag.
*   If a `src` or `href` starts with `pytron://`, it fetches the data via the bridge.
*   It creates a local `blob:` URL and hot-swaps the original attribute.
*   This makes VAP completely transparent to the developer.

### Performance Profile
*   **Latency**: < 1ms for small assets.
*   **Throughput**: Limited only by the Webview engine's string-handling speed (capable of 60FPS raw frame streaming).
*   **Memory**: Data is kept in Python memory and only copied once into a JS Blob.

## Best Practices
1.  **Keys**: Use descriptive keys (e.g., `user-avatar-101`, `model-weights`).
2.  **Cleanup**: If you are streaming (e.g., a webcam), reuse the same key. `serve_data` will overwrite the previous entry, preventing memory leaks.
3.  **Large Files**: For files on disk, VAP supports a virtual mapping. Any file in your app directory is automatically reachable via `pytron://app/path/to/file.png`.

---
*VAP is the core reason why Pytron apps feel fast even when handling heavy AI/Media workloads.*
