# Python Electron-like Library

This project aims to provide an Electron-like experience for building desktop applications using Python.
It wraps `pywebview` for the GUI and will eventually use `pyoxidizer` for packaging.

## Goals
- Simple API for creating windows and handling events.
- Bridge between Python and JavaScript.
- Standalone executable packaging.
## Features
- **Easy Window Management**: Create and manage windows with a simple Python API.
- **Two-way Communication**: Seamlessly call Python from JavaScript and evaluate JavaScript from Python.
- **Native Menus**: Create native application menus with ease.
- **Dialogs**: Native file open, save, and confirmation dialogs.
- **Standalone Packaging**: Build single-file executables using PyInstaller.

## Usage

### Creating a Window

```python
from pytron import App

app = App()
window = app.create_window("My App", "https://google.com")
app.run()
```

### JavaScript API

```python
class Api:
    def say_hello(self):
        return "Hello from Python!"

app = App()
window = app.create_window("My App", html="...", js_api=Api())
```

In JavaScript:
```javascript
const response = await pywebview.api.say_hello();
console.log(response);
```

### Native Menus

```python
from webview.menu import Menu, MenuAction

menu_items = [
    Menu('File', [
        MenuAction('Open', open_file_callback),
        MenuAction('Exit', app.quit)
    ])
]

app.run(menu=menu_items)
```
1. Install dependencies: `pip install -r requirements.txt`
2. Run the example: `python examples/hello_world.py`

## Using with React/Frontend Frameworks

You can easily integrate modern frontend frameworks like React, Vue, or Svelte.

1. Create your frontend project (e.g., using Vite).
2. Configure your build tool to use relative paths (e.g., `base: './'` in `vite.config.js`).
3. Build your frontend (`npm run build`).
4. Point your Pytron app to the built `index.html`.

See `examples/react_app.py` for a complete example.

## Building for Distribution

We use PyInstaller to package the application into a standalone executable.

### Using the Build Script

A `build.py` helper script is provided to simplify the build process.

```bash
python build.py examples/advanced_app.py --name AdvancedApp --add-data "examples/assets;assets"
```

This will create a standalone executable in the `dist` folder.

### Manual PyInstaller Command

You can also run PyInstaller directly:

```bash
pyinstaller examples/advanced_app.py --name AdvancedApp --onefile --noconsole --add-data "examples/assets;assets" --paths .
```
