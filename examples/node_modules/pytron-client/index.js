/**
 * Pytron Client Library (Final Stable Version)
 */

const state = {
    is_ready: true
};

// 2. BACKEND READINESS CHECK
const isBackendReady = () => {
    // Check for Native Bridge (Rust/Pytron Native Engine)
    if (typeof window.__pytron_native_bridge === 'function') return true;

    // Check for legacy pytron object (Chrome Engine)
    // IMPORTANT: We check if it's NOT the proxy to avoid infinite recursion
    if (window.pytron && window.pytron.is_ready && !window.pytron.__is_proxy) return true;

    // Fallback: Check for a known bound function (Legacy / Electron)
    const hasClose = typeof window.pytron_close === 'function';
    const hasDrag = typeof window.pytron_drag === 'function';

    return typeof window !== 'undefined' && (hasClose || hasDrag);
};

// 3. WAIT LOGIC (Standalone Function)
const waitForBackend = (timeout = 3000) => {
    return new Promise((resolve, reject) => {
        if (isBackendReady()) return resolve();

        console.log("[Pytron] Waiting for backend...");
        const start = Date.now();
        const interval = setInterval(() => {
            const ready = isBackendReady();
            if (ready) {
                console.log("[Pytron] Backend became ready after " + (Date.now() - start) + "ms");
                clearInterval(interval);
                resolve();
            } else if (Date.now() - start > timeout) {
                console.warn("[Pytron] Backend wait timed out. Bridge missing?");
                console.log("[Pytron Status]", {
                    hasNative: typeof window.__pytron_native_bridge,
                    hasPytron: !!window.pytron,
                    isProxy: window.pytron?.__is_proxy,
                    isReady: window.pytron?.is_ready,
                    hasChromeIPC: !!window.chrome?.webview?.postMessage
                });
                clearInterval(interval);
                resolve();
            }
        }, 50);
    });
};

// 4. EVENT LISTENERS
const eventWrappers = new Map();

// 5. PUBLIC API OBJECT (The "Real" Object)
// We define the API explicitly first.
const pytronApi = {
    state: state,
    is_ready: true,
    __is_proxy: true,

    // Expose the wait function directly
    waitForBackend: waitForBackend,

    // 4.1 Event Bus (Pub/Sub)
    events: {
        listeners: {},
        on(event, callback) {
            if (!this.listeners[event]) this.listeners[event] = [];
            this.listeners[event].push(callback);
        },
        off(event, callback) {
            if (!this.listeners[event]) return;
            this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
        },
        // internal use
        emit(event, data) {
            if (this.listeners[event]) {
                this.listeners[event].forEach(cb => {
                    try { cb(data); } catch (e) { console.error("[Pytron Event Error]", e); }
                });
            }
        }
    },

    on: (event, callback) => {
        const wrapper = (e) => callback(e.detail !== undefined ? e.detail : e);
        if (!eventWrappers.has(callback)) eventWrappers.set(callback, wrapper);
        window.addEventListener(event, wrapper);
    },

    off: (event, callback) => {
        const wrapper = eventWrappers.get(callback);
        if (wrapper) {
            window.removeEventListener(event, wrapper);
            eventWrappers.delete(callback);
        }
    },

    log: async (message) => {
        console.log(`[Pytron Client] ${message}`);
        const logFunc = window.pytron_log || window.log;
        if (typeof logFunc === 'function') {
            try { await logFunc(message); } catch (e) { /* ignore */ }
        }
    },

    /**
     * Sends an event to ALL windows including this one.
     */
    publish: async (event, data) => {
        if (typeof window.app_publish === 'function') {
            return await window.app_publish(event, data);
        }
    },

    /**
     * Helper to resolve pytron:// assets to Data URIs or Blobs
     */
    asset: async (key) => {
        // Try the optimized binary bridge first (VAP)
        if (typeof window.__pytron_vap_get === 'function') {
            try {
                const asset = await window.__pytron_vap_get(key);
                if (asset) {
                    const bytes = new Uint8Array(asset.raw.length);
                    for (let i = 0; i < asset.raw.length; i++) {
                        bytes[i] = asset.raw.charCodeAt(i);
                    }
                    return new Blob([bytes], { type: asset.mime });
                }
            } catch (e) {
                console.error("[Pytron] VAP Asset resolution failed:", e);
            }
        }

        // Fallback for legacy / slower Base64 bridge
        if (typeof window.pytron_get_asset === 'function') {
            try {
                const asset = await window.pytron_get_asset(key);
                return asset ? asset.data : null;
            } catch (e) {
                console.error("[Pytron] Legacy Asset resolution failed:", e);
                return null;
            }
        }
        return null;
    }
};

// 6. GLOBAL ASSET INTERCEPTOR
// We only hook fetch if it hasn't been handled by the Pytron Core yet
if (typeof window !== 'undefined' && !window.__pytron_fetch_interceptor_active) {
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
        let [resource] = args;
        const url = (typeof resource === 'string') ? resource :
            (resource instanceof URL ? resource.href : (resource && resource.url));

        if (url && url.startsWith('pytron://')) {
            const key = url.replace('pytron://', '').split(/[?#]/)[0];
            const asset = await pytronApi.asset(key);
            if (asset) {
                if (asset instanceof Blob) return new Response(asset);
                return originalFetch(asset); // Data URI fallback
            }
        }
        return originalFetch(...args);
    };
    window.__pytron_fetch_interceptor_active = true;
}

// 6.1 DOM OBSERVER (Automatic Image/Script/Link Injection)
// Handles <img src="pytron://..."> automatically.
if (typeof window !== 'undefined' && !window.__pytron_dom_observer_active) {
    const getPytronKey = (url) => {
        if (!url || typeof url !== 'string') return null;
        const match = url.match(/pytron:\/\/([^?#]+)/);
        return match ? match[1] : null;
    };

    const handlePytronAsset = async (el) => {
        if (!el || !el.tagName) return;
        const isLink = el.tagName === 'LINK';
        const isScript = el.tagName === 'SCRIPT';
        const attr = isLink ? 'href' : 'src';

        const rawUrl = el.getAttribute(attr);
        const key = getPytronKey(rawUrl) || getPytronKey(el[attr]);

        if (key && !el.__pytron_loading) {
            el.__pytron_loading = true;
            try {
                // console.log("[Pytron VAP] Reconciling asset key:", key, "for", el.tagName);
                const assetBlob = await pytronApi.asset(key);
                if (assetBlob) {
                    const blobUrl = URL.createObjectURL(assetBlob);

                    if (isScript) {
                        // Scripts need to be recreated to execute
                        const newScript = document.createElement('script');
                        Array.from(el.attributes).forEach(a => {
                            if (a.name !== 'src') newScript.setAttribute(a.name, a.value);
                        });
                        newScript.src = blobUrl;
                        newScript.__pytron_loading = true;
                        el.parentNode.replaceChild(newScript, el);
                    } else {
                        if (el.__pytron_blob_url) URL.revokeObjectURL(el.__pytron_blob_url);
                        el.__pytron_blob_url = blobUrl;
                        el[attr] = blobUrl;
                    }
                }
            } catch (e) {
                console.error("[Pytron VAP] DOM Asset load failed:", e);
            } finally {
                el.__pytron_loading = false;
            }
        }
    };

    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(node => {
                    if (node.tagName && ['IMG', 'SCRIPT', 'LINK'].includes(node.tagName)) handlePytronAsset(node);
                    else if (node.querySelectorAll) {
                        node.querySelectorAll('img, script, link').forEach(handlePytronAsset);
                    }
                });
            } else if (mutation.type === 'attributes') {
                if (mutation.target.tagName && ['IMG', 'SCRIPT', 'LINK'].includes(mutation.target.tagName)) {
                    handlePytronAsset(mutation.target);
                }
            }
        }
    });

    const startObserver = () => {
        const target = document.documentElement || document.body;
        if (target) {
            observer.observe(target, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['src', 'href']
            });
            // Initial scan
            document.querySelectorAll('img, script, link').forEach(handlePytronAsset);
        } else {
            // Retry if body not ready (unlikely at this stage but safe)
            setTimeout(startObserver, 20);
        }
    };

    if (document.readyState === 'loading') {
        window.addEventListener('DOMContentLoaded', startObserver);
    } else {
        startObserver();
    }

    window.__pytron_dom_observer_active = true;
}

// 6. THE PROXY (Only for dynamic Python calls)
const pytron = new Proxy(pytronApi, {
    get: (target, prop) => {
        // A. Local Method Check (Priority)
        // If the property exists on our defined API object, return it immediately.
        if (prop in target) {
            return target[prop];
        }

        // B. Ignore React/System Symbols
        if (typeof prop === 'symbol' || prop === 'then' || prop === 'toJSON') {
            return undefined;
        }

        // C. Python Bridge (Dynamic Wrapper)
        return async (...args) => {
            // 1. Wait for Backend (Using the standalone function)
            if (!isBackendReady()) {
                await waitForBackend(2000);
            }

            const directName = String(prop);

            // Check bridge specifically
            const nativeBridge = window.__pytron_native_bridge;
            const hasNative = typeof nativeBridge === 'function';

            if (hasNative) {
                try {
                    return await nativeBridge(directName, args);
                } catch (err) {
                    console.error(`[Pytron Native] Error '${directName}':`, err);
                    throw err;
                }
            }

            // Legacy/Chrome Checks
            const internalName = `pytron_${String(prop)}`;
            if (typeof window[internalName] === 'function') {
                return await window[internalName](...args);
            }
            if (typeof window[directName] === 'function') {
                return await window[directName](...args);
            }

            // 3. Not Found
            console.warn(`[Pytron] Method '${directName}' not found. Bridge Status: ${hasNative ? 'OK' : 'MISSING'}`);
            throw new Error(`Method '${directName}' not found.`);
        };
    }
});

// Setup State Listener
if (typeof window !== 'undefined') {
    // Initial Sync
    (async () => {
        await waitForBackend(3000);

        // Robust Sync: Try both the wrapper and the direct bridge
        const performSync = async () => {
            if (typeof window.pytron_sync_state === 'function') {
                return await window.pytron_sync_state();
            } else if (typeof window.__pytron_native_bridge === 'function') {
                // Fallback to direct bridge if wrapper hasn't been created by event loop yet
                return await window.__pytron_native_bridge('pytron_sync_state', []);
            }
            return null;
        };

        try {
            let initialState = null;
            // Retry briefly for initial discovery
            for (let i = 0; i < 5; i++) {
                initialState = await performSync();
                if (initialState) break;
                await new Promise(r => setTimeout(r, 100));
            }

            if (initialState) {
                Object.assign(state, initialState);

                // --- DYNAMIC PLUGIN UI INJECTION ---
                if (state.plugins && Array.isArray(state.plugins)) {
                    state.plugins.forEach(plugin => {
                        if (plugin.ui_entry) {
                            console.log(`[Pytron Client] Auto-loading Plugin UI: ${plugin.name} from ${plugin.ui_entry}`);
                            injectPlugin(plugin);
                        }
                    });
                }

                // Dispatch event so UI components can update
                window.dispatchEvent(new CustomEvent('pytron:state', { detail: { ...state } }));
            }
        } catch (e) {
            console.warn("[Pytron Client] Initial state sync failed:", e);
        }
    })();

    window.addEventListener('pytron:state-update', (e) => {
        const payload = e.detail;
        if (payload && typeof payload === 'object' && 'key' in payload) {
            state[payload.key] = payload.value;

            // 1. Dispatch specific event for the key
            const specificEvent = new CustomEvent(`state:${payload.key}`, { detail: payload.value });
            window.dispatchEvent(specificEvent);

            // 2. Dispatch legacy 'pytron:state' event with full state for components listening to everything
            const legacyEvent = new CustomEvent('pytron:state', { detail: { ...state } });
            window.dispatchEvent(legacyEvent);

            // 3. Handle Plugin Registration (if the 'plugins' key was updated)
            if (payload.key === 'plugins' && Array.isArray(payload.value)) {
                payload.value.forEach(plugin => {
                    if (plugin.ui_entry && !window.__pytron_loaded_plugins?.has(plugin.name)) {
                        injectPlugin(plugin);
                    }
                });
            }
        }
    });

    // Helper to inject plugin scripts and handle slots
    const injectPlugin = (plugin) => {
        if (!window.__pytron_loaded_plugins) window.__pytron_loaded_plugins = new Set();
        window.__pytron_loaded_plugins.add(plugin.name);

        console.log(`[Pytron Client] Loading UI for plugin: ${plugin.name} from ${plugin.ui_entry}`);

        const script = document.createElement('script');
        script.src = plugin.ui_entry;
        script.type = 'module';
        script.onload = () => {
            console.log(`[Pytron Client] Plugin script loaded: ${plugin.name}`);
            // Check for slot injection
            if (plugin.slot) {
                const containers = document.querySelectorAll(`[data-pytron-slot="${plugin.slot}"]`);
                containers.forEach(container => {
                    const el = document.createElement(`${plugin.name}-widget`);
                    container.appendChild(el);
                });
            }
        };
        document.head.appendChild(script);
    };

    // Listen for discrete plugin load events
    window.addEventListener('pytron:plugin-loaded', (e) => {
        injectPlugin(e.detail);
    });

    // Capture Global Errors
    window.addEventListener('error', (event) => {
        const errorData = {
            message: event.message,
            source: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            stack: event.error ? event.error.stack : ''
        };
        if (typeof window.pytron_report_error === 'function') {
            window.pytron_report_error(errorData).catch(() => { });
        }
    });

    // Capture Unhandled Promise Rejections
    window.addEventListener('unhandledrejection', (event) => {
        const errorData = {
            message: event.reason ? String(event.reason) : 'Unhandled Promise Rejection',
            source: 'Promise',
            stack: event.reason && event.reason.stack ? event.reason.stack : ''
        };
        if (typeof window.pytron_report_error === 'function') {
            window.pytron_report_error(errorData).catch(() => { });
        }
    });

    // IPC Queueing (Debounce Resize)
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            // Only send RPC to Python when user STOPS resizing
            // We publish this as a standard event which the backend can listen to if needed
            if (pytron.publish) {
                pytron.publish('window_resized', { width: window.innerWidth, height: window.innerHeight });
            }
        }, 100);
    });

    // Global Drag & Drop Handler (Prevent browser navigation & dispatch to backend)
    // This allows the client library to manage file drops without backend injection
    window.addEventListener('dragover', (e) => e.preventDefault(), true);
    window.addEventListener('drop', (e) => {
        e.preventDefault();

        // Use pytronApi.log to print to Python Terminal for debugging visibility
        pytronApi.log("[Pytron Client] Drop Event Detected");

        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            pytronApi.log(`[Pytron Client] Found ${e.dataTransfer.files.length} files.`);
            const files = [];
            for (let i = 0; i < e.dataTransfer.files.length; i++) {
                const f = e.dataTransfer.files[i];
                // pytronApi.log(`[Pytron Client] File[${i}]: name=${f.name}, path=${f.path}, fullPath=${f.fullPath}`);

                // WebView2 / Electron usually exposes 'fullPath' or 'path' on File objects
                // We check both for maximum compatibility
                const path = f.path || f.fullPath;
                if (path) {
                    files.push(path);
                }
            }

            // Send to backend if paths are available
            // We use the direct binding 'pytron_native_drop' if available
            if (files.length > 0) {
                if (typeof window.pytron_native_drop === 'function') {
                    pytronApi.log("[Pytron Client] Dispatching to backend via pytron_native_drop");
                    window.pytron_native_drop(files);
                } else {
                    pytronApi.log("[Pytron Client] WARNING: window.pytron_native_drop is not defined!");
                }
            } else {
                pytronApi.log("[Pytron Client] WARNING: No paths could be extracted from dropped files. Browser Security may be blocking path access.");
            }
        }
    }, true);
}

// 7. ATTACH TO WINDOW
// 7. ATTACH TO WINDOW
if (typeof window !== 'undefined') {
    // Aggressive Assignment: We want our Proxy to be the primary window.pytron
    // but we preserve any existing properties (like .id or .is_ready)
    if (!window.pytron || !window.pytron.__is_proxy) {
        const existing = window.pytron;
        window.pytron = pytron;
        if (existing) {
            Object.assign(pytronApi, existing);
            if (existing.state) Object.assign(state, existing.state);
        }
    } else {
        // console.log("[Pytron Client] Primary proxy already active.");
    }

    // Backwards compatibility for templates using pytronApi
    if (!window.pytronApi) {
        window.pytronApi = pytronApi;
    }
}

export default pytron;

