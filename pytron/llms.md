# Pytron AI Guide

This guide is intended for AI agents (LLMs) to understand how to interact with, develop, and extend the Pytron framework.

## 🚀 Overview

Pytron is an Electron-like framework for Python that allows developers to build desktop applications using Python for the backend and modern Web technologies (React, Vue, Vite, etc.) for the frontend.

### Core Architecture
- **Pytron Kit (`pytron`)**: The Python backend that manages application windows, handles IPC, and synchronizes state.
- **Pytron Client (`pytron-client`)**: A JavaScript/TypeScript library that provides an RPC bridge and state synchronization in the frontend.
- **Pytron UI (`pytron-ui`)**: A React-based UI component library designed for building native-feeling desktop applications.

---

## 🛠 Backend Development (Python)

### 1. The `App` Instance
The entry point of any Pytron application is the `App` class.
```python
from pytron import App
app = App()
```

### 2. Exposing Functions
Functions can be exposed to the frontend using the `@app.expose` decorator.
```python
@app.expose
def greet(name: str):
    return f"Hello, {name}!"
```
*Note: Pytron automatically generates TypeScript definitions for these functions.*

### 3. Reactive State
Pytron maintains a reactive state shared between Python and the frontend via `app.state`.
```python
app.state.user = {"name": "Alice", "role": "admin"}
```
Any change to `app.state` is automatically synchronized to the frontend.

---

## 🌐 Frontend Development (JS/TS)

### 1. Calling Python Functions
Use the `pytron` client (usually a proxy) to call exposed Python functions.
```javascript
import pytron from 'pytron-client';

const result = await pytron.greet("Agent");
```

### 2. Consuming State
Listen for state updates to react to backend changes.
```javascript
pytron.on('pytron:state-update', (change) => {
    console.log("State updated:", change);
});
```

---

## 📁 Project Structure & Key Files

- `pytron/application.py`: Main `App` class and window orchestration.
- `pytron/webview.py`: Integration with system WebView (Edge WebView2, WebKit, etc.).
- `pytron/state.py`: Reactive state implementation.
- `pytron/cli.py`: Command line interface for project management.
- `pyproject.toml`: Package configuration and dependencies.

---

## ⌨️ CLI Commands

- `pytron init`: Initialize a new project from templates.
- `pytron run`: Start the application in development mode with hot-reloading.
- `pytron build`: Package the app into a standalone executable.

---

## 💡 Best Practices for LLMs
1. **Always use `@app.expose`** for functions you want the UI to call.
2. **Prefer `app.state`** for data synchronization rather than frequent RPC calls if the data needs to be reactive.
3. **Check `application.py`** for window management settings (width, height, title, frameless mode).
4. **Use Type Hints** in Python functions; they are used to generate accurate TypeScript definitions.

---

## 📱 Android Development

Pytron supports building and deploying applications to Android devices.

### Commands
- `pytron android init`: Initialize Android project.
- `pytron android sync`: Sync python code and frontend to Android project. **Automatically re-compiles C-extensions using NDK.**
- `pytron android run`: Install and run the app on connected device.
- `pytron android logcat`: View device logs.

