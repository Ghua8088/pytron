import os
import sys
from pytron import App

# Setup example directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = App()


@app.expose
def setup_demo():
    # Ensure dependencies like PIL are available or fail gracefully
    # This creates a dummy icon if it doesn't exist
    icon_path = os.path.join(FRONTEND_DIR, "icon.png")
    if not os.path.exists(icon_path):
        try:
            from PIL import Image

            img = Image.new("RGB", (64, 64), color=(99, 102, 241))
            img.save(icon_path)
            print(f"Created demo icon at {icon_path}")
        except Exception as e:
            print(f"Could not create demo icon: {e}")

    return "Demo environment ready."


if __name__ == "__main__":
    # Ensure the demo environment is ready on startup
    setup_demo()
    app.run()
