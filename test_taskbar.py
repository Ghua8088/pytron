from pytron import App


def main():
    # Load Pytron without a settings file for an isolated test
    app = App(
        config_file="dummy.json"
    )  # Pytron requires a string, but it will fallback to defaults if not found

    # Manually configure the window properties
    app.config.update(
        {
            "title": "Taskbar Hider Test",
            "hide_from_taskbar": True,  # THIS TRIGGERS THE RUST BINDINGS
            "dimensions": [400, 300],
            # A simple data URL so we don't need a frontend bundle
            "url": "data:text/html,<body style='background: #222; color: #fff; font-family: sans-serif; text-align: center; padding-top: 50px;'><h1>Look at your taskbar!</h1><p>(I shouldn't be there)</p></body>",
            "engine": "native",
        }
    )

    print("[TEST] Running Taskbar Test...")
    app.run()


if __name__ == "__main__":
    main()
