# RFC: Native Protocol Implementation (`pytron://`)

To replace the brittle JavaScript interceptors in `pytron-client` with a robust native solution, we must implement a **Custom Scheme Handler** in the `pytron` native backend.

Since your implementation is C++ based (using `webview/webview` with WebView2/WebKit), you need to modify the C++ source code of your DLL/Shared Library to register the `pytron://` scheme.

## 1. C++ Implementation Guide

You need to inject the protocol registration logic **before** the main loop starts or **during** webview creation.

### A. Windows (WebView2)
For the `webview` library wrapper on Windows, you interact with `ICoreWebView2`. This typically requires hooking into the initialization callback.

**File:** `webview.cc` (or your equivalent implementation file)

```cpp
// 1. Include necessary headers
// Ensure you have access to <WebView2.h> interfaces

// 2. In your initialization logic (usually inside the `webview::webview` constructor or `embed` function)

// Step A: Allow File Access (Crucial for loading local resources)
// When creating the environment options:
auto options = Microsoft::WRL::Make<CoreWebView2EnvironmentOptions>();
options->put_AdditionalBrowserArguments(L"--allow-file-access-from-files");

// Step B: Register the Scheme Handler (When the controller is created)
webview2->AddWebResourceRequestedFilter(L"pytron*", COREWEBVIEW2_WEB_RESOURCE_CONTEXT_ALL);

EventRegistrationToken token;
webview2->add_WebResourceRequested(
    Callback<ICoreWebView2WebResourceRequestedEventHandler>(
        [](ICoreWebView2* sender, ICoreWebView2WebResourceRequestedEventArgs* args) -> HRESULT {
            
            // 1. Get the URI
            LPWSTR uri_ptr;
            args->get_Request(nullptr); // Just to verify request exists
            ICoreWebView2WebResourceRequest* request;
            args->get_Request(&request);
            request->get_Uri(&uri_ptr);
            std::wstring uri(uri_ptr);
            CoTaskMemFree(uri_ptr);

            // 2. Check Scheme
            if (uri.find(L"pytron://") == 0) {
                
                // 3. Parse Path (pytron://app/assets/logo.png -> app/assets/logo.png)
                std::wstring path_str = uri.substr(9); // Strip 'pytron://'
                
                // Convert to std::string for file processing if needed
                // std::string path = ...

                // 4. Read File (Implement your safe file reader here)
                // std::vector<char> content = ReadFileSafe(path);

                if (!content.empty()) {
                    // 5. Create Response Stream
                    IStream* stream = SHCreateMemStream((const BYTE*)content.data(), content.size());
                    
                    // 6. Create Response
                    ICoreWebView2WebResourceResponse* response;
                    env->CreateWebResourceResponse(
                        stream, 
                        200, 
                        L"OK", 
                        L"Content-Type: image/png", // You must implement simple mime sniffing!
                        &response
                    );

                    args->put_Response(response);
                    return S_OK;
                }
            }

            return S_OK;
        }).Get(), &token);
```

### B. Linux (WebKitGTK)
For `webview` on Linux:

```cpp
// In your initialization:
WebKitWebContext *context = webkit_web_context_get_default();
webkit_web_context_register_uri_scheme(context, "pytron", 
    [](WebKitURISchemeRequest *request, gpointer user_data) {
        
        const gchar *uri = webkit_uri_scheme_request_get_uri(request);
        // Parse uri...
        
        GInputStream *stream = ...; // Create stream from file
        webkit_uri_scheme_request_finish(request, stream, -1, "image/png");
        g_object_unref(stream);
    }, nullptr, nullptr);
```

### C. macOS (Cocoa/WebKit)
For `WKWebView`:

```objective-c
// In your configuration
[config setURLSchemeHandler:pytronHandler forURLScheme:@"pytron"];
```

---

## 2. Enabling the Native Switch in Client

Once your DLL is updated with the logic above, you must tell the `pytron-client` to stop using its JS Polyfills.

**Method A (Recommended): Auto-Injection**
In your C++ `webview_init` or equivalent (where you inject `window.pytron = ...`), add:

```cpp
// Inject this flag before loading other scripts
webview_init(w, "window.__pytron_native_scheme = true;");
```

**Method B: Manual Config**
Update your Python `webview.py` to inject it:

```python
# pytron/webview.py

init_js += "window.__pytron_native_scheme = true;"
```

## 3. Benefits of this Change

| Feature | JS Interceptor (Old) | Native Protocol (New) |
| :--- | :--- | :--- |
| **Images** | ⚠️ Flicker (Race Condition) | ✅ Instant |
| **CSS** | ❌ Not Supported | ✅ Native Support |
| **Video** | ⚠️ Blob URL only | ✅ Streaming Support |
| **Performance** | 🔻 High Overhead (Observer) | ⚡ Zero JS Overhead |
| **Stability** | ⚠️ DOM Mutation Risks | 🛡️ Standard Browser Feature |
