/**
 * Pytron Client Library
 * Provides a seamless bridge to the Python backend.
 */

// Event storage
const listeners = {};

// The main Pytron Proxy
const pytron = new Proxy({
    /**
     * Listen for an event sent from the Python backend.
     * @param {string} event - The event name.
     * @param {function} callback - The function to call when event triggers.
     */
    on: (event, callback) => {
        if (!listeners[event]) listeners[event] = [];
        listeners[event].push(callback);
    },

    /**
     * Remove an event listener.
     * @param {string} event - The event name.
     * @param {function} callback - The function to remove.
     */
    off: (event, callback) => {
        if (!listeners[event]) return;
        listeners[event] = listeners[event].filter(cb => cb !== callback);
    }
}, {
    get: (target, prop) => {
        // Return local methods if they exist (on, off)
        if (prop in target) return target[prop];

        // Otherwise, proxy to the backend
        return async (...args) => {
            if (typeof window === 'undefined' || !window.pywebview || !window.pywebview.api) {
                console.warn(`[Pytron] Backend not connected. Call to '${String(prop)}' failed.`);
                throw new Error("Pytron backend not connected");
            }

            if (typeof window.pywebview.api[prop] !== 'function') {
                // Check if it's a system method (nested under 'system')
                // This is a simple heuristic; for a deeper nesting we might need a recursive proxy,
                // but for now let's keep it flat or assume the user calls pytron.system_notification()
                // or we can expose system methods as top level 'system_...'
                throw new Error(`Method '${String(prop)}' not found on Pytron backend.`);
            }

            try {
                return await window.pywebview.api[prop](...args);
            } catch (error) {
                console.error(`[Pytron] Error calling '${String(prop)}':`, error);
                throw error;
            }
        };
    }
});

// Internal dispatcher called by Python
window.__pytron_dispatch = (event, data) => {
    if (listeners[event]) {
        listeners[event].forEach(cb => cb(data));
    }
};

export default pytron;
