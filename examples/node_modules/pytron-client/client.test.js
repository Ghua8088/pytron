/**
 * @jest-environment jsdom
 */

import { jest, describe, expect, test, beforeEach, afterEach } from '@jest/globals';
import pytron, { default as pytronDefault } from './index.js';

describe('Pytron Client', () => {
    let windowSpy;

    beforeEach(async () => {
        // Mock Window and DOM
        // Note: In pure ESM, we can't easily reset modules and re-import 'pytron' 
        // to re-trigger the top-level init code (like the MutationObserver).
        // However, we can inspect 'pytron' which is the default export.

        // Setup mocks needed by the library's side effects
        window.pytron_close = jest.fn();
        window.pytron_minimize = jest.fn();
        window.pytron_drag = jest.fn();

        // Note: The side-effects in index.js (attaching to window) happen 
        // when the module is first imported. They won't re-run in beforeEach here.
        // We have to test the *state* of window.pytron.
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('should attach to window object', () => {
        // Assert that import worked and attached global
        expect(window.pytron).toBeDefined();
        // Index.js logic: window.pytron = pytron;
        expect(window.pytron).toBe(pytron);
    });

    test('state management (local)', () => {
        window.pytron.state.ver = '2.0.0';
        expect(pytron.state.ver).toBe('2.0.0');
    });

    test('event listener registration (on/off)', () => {
        const callback = jest.fn();
        pytron.on('test-event', callback);

        // Simulate event
        const event = new CustomEvent('test-event', { detail: { foo: 'bar' } });
        window.dispatchEvent(event);

        expect(callback).toHaveBeenCalledWith({ foo: 'bar' });

        // Test off
        pytron.off('test-event', callback);
        window.dispatchEvent(event);
        expect(callback).toHaveBeenCalledTimes(1);
    });

    // We can't really re-test "waitForBackend" properly inside one test run 
    // if the module state is singleton. 
    // But we can test that calling it works.
    test('waitForBackend resolves', async () => {
        // Ensure backend functions exist so it resolves immediately or quickly
        window.pytron_close = jest.fn();
        const p = pytron.waitForBackend(100);
        await expect(p).resolves.toBeUndefined();
    });

    test('dynamic proxy should call native functions', async () => {
        window.pytron_test_func = jest.fn().mockReturnValue('esm-success');

        // calling undefined method on the proxy triggers the dynamic lookup
        const result = await pytron.test_func('arg1');

        expect(window.pytron_test_func).toHaveBeenCalledWith('arg1');
        expect(result).toBe('esm-success');
    });

});
