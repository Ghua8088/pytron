import os
import sys

# Add parent directory to path to import pytron
# This is needed because we are running from examples/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pytron import App

def main():
    app = App()
    
    # Path to the built React app
    # We point to the index.html in the dist folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    react_dist = os.path.join(current_dir, 'react_ui', 'dist', 'index.html')
    
    if not os.path.exists(react_dist):
        print(f"React app not found at: {react_dist}")
        print("Please run 'npm install' and 'npm run build' in examples/react_ui")
        return

    print(f"Loading app from: {react_dist}")

    window = app.create_window(
        title="Pytron React App",
        url=react_dist,
        width=1000,
        height=800,
        resizable=True,
        frameless=True,
        easy_drag=True
    )
    
    # Expose a Python function to JavaScript
    def python_func(params):
        print(f"JavaScript called Python with: {params}")
        return f"Python received: {params}"
    
    # Expose functions using the new expose method
    window.expose(python_func)
    
    def add(a, b):
        print(f"Adding {a} + {b}")
        return a + b
        
    window.expose(add)
    
    app.run(debug=True)

if __name__ == '__main__':
    main()
