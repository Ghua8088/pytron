import argparse
import importlib.util
import os
import sys

from pytron.console import log


def cmd_docs(args: argparse.Namespace) -> int:
    """
    Logic for the 'pytron docs' command.
    Discovers the Pytron application and triggers documentation generation.
    """
    script = args.script or "app.py"
    if not os.path.exists(script):
        log(
            f"[bold red]Error:[/] Entrypoint script '{script}' not found in current directory."
        )
        return 1

    # 1. Enable Headless Mode to prevent unwanted window creation during import
    os.environ["PYTRON_HEADLESS"] = "1"

    log(f"🔍 [bold cyan]Discovering API from {script}...[/]")

    try:
        # 2. Setup the environment to import the user script
        current_dir = os.path.abspath(os.path.dirname(script))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)

        # 3. Robust Discovery Hooks
        from pytron.application import App

        recorded_instances = []
        original_init = App.__init__
        original_run = App.run

        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            recorded_instances.append(self)

        def mock_run(*args, **kwargs):
            log("   [dim]Discovery Session: Bypassing app.run()[/]")

        # Apply patches
        App.__init__ = patched_init
        App.run = mock_run

        # 4. Import logic
        module_name = "pytron_app_discovery"
        spec = importlib.util.spec_from_file_location(module_name, script)
        if not spec or not spec.loader:
            log(f"[bold red]Error:[/] Could not load module spec for {script}")
            return 1

        module = importlib.util.module_from_spec(spec)

        # 5. Execute module to trigger decorators (@app.expose, etc.)
        try:
            spec.loader.exec_module(module)
        except SystemExit:
            pass
        except Exception as e:
            log(f"   [yellow]Warning:[/] Module execution encountered an error: {e}")

        # 6. Check if we have an instance yet
        app_instance = None
        if recorded_instances:
            app_instance = recorded_instances[0]
        else:
            # Maybe it is in main()?
            main_func = getattr(module, "main", None)
            if callable(main_func):
                log("   [dim]No global App found. Attempting to call main()...[/]")
                try:
                    main_func()
                    if recorded_instances:
                        app_instance = recorded_instances[0]
                except Exception as e:
                    log(f"   [yellow]Warning:[/] Calling main() failed: {e}")

        if not app_instance:
            log(
                "[bold red]Error:[/] No 'App' instance was created during the discovery phase."
            )
            return 1

        # 7. Trigger the Generator
        output_dir = args.output or "docs"
        log(f"🛠️  [bold cyan]Building documentation in '{output_dir}'...[/]")

        app_instance.generate_docs(output_dir)

        log("\n✨ [bold green]Pytron Documentation Ready![/]")
        log(f"   Path: [underline]{os.path.abspath(output_dir)}/index.html[/]")
        return 0

    except Exception as e:
        log(f"[bold red]Critical Failure:[/] {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        # Restore the original run method
        App.run = original_run
        # Clean up headless flag if needed, though often not necessary as process exits
        if "PYTRON_HEADLESS" in os.environ:
            del os.environ["PYTRON_HEADLESS"]
