from pytron import App

def main():
    app = App()
    window = app.create_window()
    def hello(name):
        print("hello")
        return f"Hello {name}"
    window.expose(hello)
    app.run(debug=True)

if __name__ == '__main__':
    main()
