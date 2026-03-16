import logging
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from pytron import App


def main():
    logging.basicConfig(level=logging.INFO)

    app = App(
        {
            "engine": "servo",
            "debug": True,
            "title": "Servo Test",
            "url": "https://google.com",
        }
    )

    @app.expose
    def hello(name):
        print(f"Hello from Python: {name}")
        return f"Greetings, {name}!"

    app.run()


if __name__ == "__main__":
    main()
