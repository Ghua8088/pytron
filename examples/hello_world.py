import sys
import os

# Add the project directory to sys.path so we can import pytron
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pytron import App

class Api:
    def say_hello(self, name):
        print(f"Hello, {name}!")
        return f"Hello, {name}!"

def main():
    app = App()
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f0f0; }
            .container { text-align: center; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            button { padding: 10px 20px; font-size: 16px; cursor: pointer; background-color: #007bff; color: white; border: none; border-radius: 4px; }
            button:hover { background-color: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Hello from Pytron!</h1>
            <p>This is a desktop app built with Python and HTML/CSS.</p>
            <button onclick="pywebview.api.say_hello('User').then(alert)">Call Python</button>
        </div>
    </body>
    </html>
    """

    api = Api()
    app.create_window("Hello Pytron", html=html_content, js_api=api)
    app.run(debug=True)

if __name__ == "__main__":
    main()
