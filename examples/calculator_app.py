import os
import sys

# Add parent directory to path to import pytron
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pytron import App, get_resource_path

def main():
    app = App()
    
    # Path to the built React app
    # Use get_resource_path to ensure it works in both dev and frozen (PyInstaller) modes
    react_dist = get_resource_path(os.path.join('react_ui', 'dist', 'index.html'))
    
    if not os.path.exists(react_dist):
        # Fallback for dev mode if running from root and not using get_resource_path logic correctly for dev
        # Try relative to current file if the above fails in dev
        current_dir = os.path.dirname(os.path.abspath(__file__))
        react_dist_fallback = os.path.join(current_dir, 'react_ui', 'dist', 'index.html')
        if os.path.exists(react_dist_fallback):
            react_dist = react_dist_fallback
        else:
            print(f"React app not found at: {react_dist}")
            return

    # Create a smaller, fixed-size window for the calculator
    window = app.create_window(
        title="Pytron Calculator",
        url=react_dist,
        width=1000,
        height=1000,
        resizable=True,
        frameless=True,
        easy_drag=True
    )
    
    # Calculator Logic
    def calculate(expression):
        print(f"Calculating: {expression}")
        try:
            # Security check: only allow safe characters
            allowed_chars = set("0123456789.+-*/() ")
            if not all(c in allowed_chars for c in expression):
                return "Invalid Input"
            
            # Evaluate the expression
            # In a real app, use a safer parser than eval
            result = eval(expression)
            
            # Format result to avoid long decimals if possible
            if isinstance(result, float) and result.is_integer():
                return str(int(result))
            return str(result)
        except Exception as e:
            print(f"Error: {e}")
            return "Error"

    window.expose(calculate)
    
    app.run(debug=True)

if __name__ == '__main__':
    main()
