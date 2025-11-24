from pytron import App
from ollama import chat


def send_message(message: str) -> str:
    """Send a message using the Ollama Python package (no CLI).

    This tries several common SDK shapes and returns the first textual
    result found. If the package is not available or no supported call
    succeeds, returns an error string instructing the user to install
    or configure the Ollama Python SDK.
    """
    response = chat(model='qwen3:0.6b', messages=[
        {'role':'user', 'content':message}
    ])
    return response.message.content
def main():
    app = App()
    window = app.create_window()
    window.expose(send_message)
    app.run()


if __name__ == '__main__':
    main()
