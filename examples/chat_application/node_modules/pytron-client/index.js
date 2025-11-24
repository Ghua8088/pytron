/**
 * Pytron Client Library
 * Provides a seamless bridge to the Python backend.
 */

const pytron = new Proxy({}, {
    get: (target, prop) => {
        return async (...args) => {
            // Check if pywebview is available
            if (typeof window === 'undefined' || !window.pywebview || !window.pywebview.api) {
                console.warn(`[Pytron] Backend not connected. Call to '${String(prop)}' failed.`);
                throw new Error("Pytron backend not connected");
            }

            // Check if the method exists on the API
            if (typeof window.pywebview.api[prop] !== 'function') {
                throw new Error(`Method '${String(prop)}' not found on Pytron backend.`);
            }

            // Call the method
            try {
                return await window.pywebview.api[prop](...args);
            } catch (error) {
                console.error(`[Pytron] Error calling '${String(prop)}':`, error);
                throw error;
            }
        };
    }
});
export default pytron;
