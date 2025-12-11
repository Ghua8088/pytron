
# Banner: pytron.png
![Pytron](pytron-banner.png)
# Pytron

Pytron is a modern framework for building desktop applications using Python for the backend and web technologies (React, Vite) for the frontend. It combines the power of Python's ecosystem with the rich user interfaces of the web.

## Features

*   **Type-Safe Bridge**: Automatically generate TypeScript definitions (`.d.ts`) from your Python code.
*   **Reactive State**: Synchronize state seamlessly between Python and JavaScript.
*   **Advanced Serialization**: Built-in support for Pydantic models, PIL Images, UUIDs, and more.
*   **System Integration**: Native file dialogs, notifications, and shortcuts.
*   **Developer Experience**: Hot-reloading, automatic virtual environment management, and easy packaging.

## Prerequisites

- **Python 3.7+**
- **Node.js & npm** (for frontend development)

## Quick Start

1.  **Install Pytron**:
    ```bash
    pip install pytron-kit
    ```

2.  **Initialize a New Project**:
    This command scaffolds a new project, creates a virtual environment (`env/`), installs initial dependencies, and sets up a frontend.
    ```bash
    # Default (React + Vite)
    pytron init my_app

    # Using a specific template (vue, svelte, next, etc.)
    pytron init my_app --template next
    ```
    Supported templates: `react` (default), `vue`, `svelte`, `next` (Next.js), `vanilla`, `preact`, `lit`, `solid`, `qwik`.

3.  **Install project dependencies (recommended)**:
    After cloning or when you need to install/update dependencies for the project, use the CLI-managed installer which will create/use the `env/` virtual environment automatically:
    ```bash
    # Creates env/ if missing and installs from requirements.txt
    pytron install
    ```

    Notes:
    - This creates an `env/` directory in the project root (if not already present) and runs `pip install -r requirements.txt` inside it.
    - All subsequent `pytron` commands (`run`, `package`, etc.) will automatically prefer the project's `env/` Python when present.

4.  **Run the App**:
    Start the app in development mode (hot-reloading enabled). The CLI will use `env/` Python automatically if an `env/` exists in the project root.
    *   **Windows**: `run.bat`
    *   **Linux/Mac**: `./run.sh`
    
    Or manually via the CLI:
    ```bash
    pytron run --dev
    ```

## Core Concepts

### 1. Exposing Python Functions
Use the `@app.expose` decorator to make Python functions available to the frontend.

```python
from pytron import App
from pydantic import BaseModel

app = App()

class User(BaseModel):
    name: str
    age: int

@app.expose
def get_user(user_id: int) -> User:
    return User(name="Alice", age=30)

app.generate_types() # Generates frontend/src/pytron.d.ts
app.run()
```

### 2. Calling from Frontend
Import the client and call your functions with full TypeScript support.
any  registered function with "pytron_" prefix will be available as pytron_{function_name}
and will not be proxied into the pytron object.
```typescript
import pytron from 'pytron-client';

async function loadUser() {
    const user = await pytron.get_user(1);
    console.log(user.name); // Typed as string
}
```

### 3. Reactive State
Sync data automatically.

**Python:**
```python
app.state.counter = 0
```

**JavaScript:**
```javascript
console.log(pytron.state.counter); // 0

// Listen for changes
pytron.on('pytron:state-update', (change) => {
    console.log(change.key, change.value);
});
```

### 4. Window Management
Control the window directly from JS.

```javascript
pytron.minimize();
pytron.toggle_fullscreen();
pytron.close();
```

## Configuration (settings.json)

Pytron uses a `settings.json` file in your project root to manage application configuration. This keeps your code clean and separates config from logic.

**Example `settings.json`:**
```json
{
    "title": "pytron app",
    "pytron_version": "0.2.2",
    "frontend_framework": "react",
    "dimensions":[800,600],
    "frameless": false,
    "url": "frontend/dist/index.html",
    "icon": "assets/icon.ico",
    "version": "1.0.0"
}
```

*   **title**: The window title and the name of your packaged executable.
*   **pytron_version**: The version of Pytron used to create the project (used for compatibility checks).
*   **frontend_framework**: The framework used (e.g., "react", "next").
*   **icon**: Path to your application icon (relative to project root). Supports `.ico` (preferred) or `.png`.
*   **url**: Entry point for the frontend (usually the built `index.html`).
*   **width/height**: Initial window dimensions.

## UI Components

Pytron provides a set of UI components to help you build a modern desktop application.
They have preimplemented window controls and are ready to use.With many useful predefined functions its very simple to use just give it a try.
# Usage
```bash
npm install pytron-ui
```
then import the webcomponents into your frontend app
```javascript
import "pytron-ui/webcomponents/TitleBar.js";
//usage
<pytron-title-bar></pytron-title-bar>
//for react
import { TitleBar } from "pytron-ui/react";
//usage
<TitleBar></TitleBar>
```
## Packaging

Distribute your app as a standalone executable. Pytron automatically reads your `settings.json` to determine the app name, version, and icon.

1.  **Build**:
    ```bash
    pytron package
    ```
    This uses PyInstaller to bundle your app. It will:
    *   Use the `title` from `settings.json` for the executable name.
    *   Use the `icon` from `settings.json` for the app icon.
    *   Automatically exclude `node_modules`.
    *   Include your `settings.json` and frontend assets.

2.  **Create Installer (NSIS)**:
    ```bash
    pytron package --installer
    ```

## CLI Reference

*   `pytron init <name> [--template <name>]`: Create a new project.
    *   `--template`: Frontend framework to use (default: `react`). Supports `next`, `vue`, `svelte`, etc.
*   `pytron install`: Create/use project `env/` and install dependencies from `requirements.txt`.
*   `pytron run [--dev]`: Run the application.
*   `pytron package [--installer]`: Build for distribution (uses `settings.json`).
*   `pytron info`: Show environment and project details.
*   `pytron build-frontend <folder>`: Build the frontend app.

---

**Happy Coding with Pytron!**
