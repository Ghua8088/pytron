# Pytron Development Guide

This guide provides a step-by-step walkthrough for building desktop applications using the Pytron framework. Pytron combines the power of Python's backend capabilities with the rich user interface of modern web frameworks like React.

## Prerequisites

- **Python 3.7+**
- **Node.js & npm** (for frontend development)

## Step 1: Project Setup

1.  **Clone/Create Project**: Start with the Pytron project structure.
2.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Step 2: Frontend Setup (React + Vite)

We recommend using Vite for a fast and modern development experience.

1.  **Initialize React App**:
    Navigate to your examples or project folder and run:
    ```bash
    npm create vite@latest my_app_ui -- --template react
    cd my_app_ui
    npm install
    ```

2.  **Install Pytron Client**:
    Install the bridge library to communicate with Python.
    ```bash
    npm install ../../js/pytron-client
    ```
    *(Adjust the path to point to the `js/pytron-client` folder in your Pytron repo)*

3.  **Configure Vite**:
    Edit `vite.config.js` to ensure assets load correctly in a local environment (relative paths).
    ```javascript
    import { defineConfig } from 'vite'
    import react from '@vitejs/plugin-react'

    export default defineConfig({
      plugins: [react()],
      base: './', // CRITICAL: Use relative paths for assets
    })
    ```

4.  **Build the Frontend**:
    ```bash
    npm run build
    ```
    This creates a `dist` folder containing your compiled HTML/CSS/JS.

## Step 3: Backend Setup (Python)

Create a Python script (e.g., `my_app.py`) to launch your application.

1.  **Import Pytron**:
    ```python
    from pytron import App
    import os
    ```

2.  **Initialize App and Window**:
    ```python
    def main():
        app = App()
        
        # Point to your built React app
        html_path = os.path.abspath("my_app_ui/dist/index.html")
        
        window = app.create_window(
            title="My Pytron App",
            url=html_path,
            width=800,
            height=600,
            resizable=True,
            frameless=False # Set to True for custom UI
        )
    ```

3.  **Define and Expose Logic**:
    Create functions you want to call from JavaScript and expose them.
    ```python
        def greet(name):
            return f"Hello, {name}! From Python."
            
        # Expose the function to the frontend
        window.expose(greet)
        
        app.run(debug=True)

    if __name__ == '__main__':
        main()
    ```

## Step 4: Connecting Frontend & Backend

Now, use the exposed Python functions in your React components.

1.  **Import Client**:
    ```javascript
    import pytron from 'pytron-client'
    ```

2.  **Call Python Functions**:
    Pytron functions are asynchronous.
    ```javascript
    async function handleGreet() {
      try {
        const message = await pytron.greet("User");
        console.log(message); // "Hello, User! From Python."
      } catch (err) {
        console.error("Error calling backend:", err);
      }
    }
    ```

## Step 5: Advanced UI (Frameless Window)

For a native app feel, use a frameless window and create a custom title bar.

1.  **Backend**: Set `frameless=True` in `create_window`.
2.  **Frontend**: Create a TitleBar component.
    ```jsx
    function TitleBar() {
      return (
        <div className="titlebar">
          <div className="drag-region">My App</div>
          <button onClick={() => pytron.minimize()}>-</button>
          <button onClick={() => pytron.close()}>x</button>
        </div>
      )
    }
    ```
3.  **CSS**:
    ```css
    .titlebar {
      display: flex;
      justify-content: space-between;
      background: #333;
      color: white;
      padding: 5px;
      user-select: none;
    }
    .drag-region {
      flex: 1;
      /* This is handled by Pytron's easy_drag or custom implementation */
    }
    ```

## Step 6: Running the App

1.  **Rebuild Frontend** (if changed):
    ```bash
    cd my_app_ui
    npm run build
    ```
2.  **Run Python Script**:
    ```bash
    cd ..
    python my_app.py
    ```

## Step 7: Packaging (Optional)

To distribute your app as a standalone `.exe`:

```bash
pyinstaller my_app.py --name MyApp --onefile --noconsole --add-data "my_app_ui/dist;my_app_ui/dist"
```

---

**Happy Coding with Pytron!**
