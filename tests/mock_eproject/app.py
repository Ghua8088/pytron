from pytron import App
import sys
import os

# Mock relative imports
sys.path.append(os.path.dirname(__file__))


def register_filesystem_routes(app):
    """
    Filesystem API for ECode.
    """

    @app.expose
    def read_file(path: str) -> str:
        """Reads a file from the disk."""
        return "file content"

    @app.expose
    def write_file(path: str, content: str) -> bool:
        """Writes content to a file."""
        return True


def main():
    app = App()
    register_filesystem_routes(app)
    app.run()


if __name__ == "__main__":
    main()
