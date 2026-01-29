![Pytron](https://raw.githubusercontent.com/Ghua8088/pytron/main/pytron-banner.png)

# Pytron Kit

[![PyPI Version](https://img.shields.io/pypi/v/pytron-kit.svg)](https://pypi.org/project/pytron-kit/)
[![Downloads](https://img.shields.io/pypi/dm/pytron-kit.svg)](https://pypi.org/project/pytron-kit/)
[![License](https://img.shields.io/pypi/l/pytron-kit.svg)](https://pypi.org/project/pytron-kit/)
[![GitHub](https://img.shields.io/badge/github-repo-000000?logo=github)](https://github.com/Ghua8088/pytron)
[![Website](https://img.shields.io/badge/official-website-blue)](https://pytron-kit.github.io/)


**Pytron-kit** is a high-performance framework for building native ("parasitic") desktop apps using Python and Web Technologies (React, Vite). It combines the computational depth of Python (AI/ML) with the UI flexibility of the web, achieving a **~5MB footprint** by utilizing the OS-native webview.

## Linux Requirements
On **Ubuntu/Debian**, you must install the WebKitGTK headers and glib bindings before installing Pytron:

```bash
sudo apt-get install -y libcairo2-dev libgirepository-2.0-dev libglib2.0-dev pkg-config python3-dev libwebkit2gtk-4.1-dev gir1.2-gtk-4.0
```

## Quick Start

```bash
# 1. Install
pip install pytron-kit

# 2. Create Project (React + Vite)
pytron init my_app

# 3. Run (Hot-Reloading)
pytron run --dev
```

## Hello World

**Python Backend** (`main.py`)
```python
from pytron import App

app = App()

@app.expose
def greet(name: str):
    return f"Hello, {name} from Python!"

app.run()
```

**Frontend** (`App.jsx`)
```javascript
import pytron from 'pytron-client';

const msg = await pytron.greet("User");
console.log(msg); // "Hello, User from Python!"
```

##  Key Features

*   **Adaptive Runtime**: Use the **Native Webview** (~5MB) for efficiency or switch to the **Chrome Engine** (Electron) for 100% rendering parity.
*   **Zero-Copy Bridge**: Stream raw binary data (video/tensors) from Python to JS at 60FPS via `pytron://`, bypassing Base64 overhead.
*   **Type-Safe**: Automatically generates TypeScript definitions (`.d.ts`) from your Python type hints.
*   **Fortress Security**: (Optional) Encrypts your Python source code and runs it via a Rust bootloader to prevent decompilation.
*   **Native Integration**: Global shortcuts, Taskbar progress, System Tray, and Native File Dialogs.

## Packaging

```bash
# Standard Build (One-file executable)
pytron package

# Secure Build (Rust Bootloader + Encryption)
pytron package --secure

# Chrome Build (Bundles Electron Engine)
pytron package --chrome
```

## Documentation

*   **[User Guide](USAGE.md)**: Configuration, advanced APIs, and UI components.
*   **[Architecture](ARCHITECTURE.md)**: Deep dive into the internal engineering and philosophy.
*   **[Roadmap](ROADMAP.md)**: Upcoming features.
*   **[Contributing](CONTRIBUTING.md)**: How to help.

## License
Apache License 2.0
