import argparse
from pathlib import Path
from ..console import (
    console,
    log,
    get_progress,
    run_command_with_output,
    Rule,
)
from .harvest import generate_nuclear_hooks
from .helpers import (
    get_python_executable,
    get_venv_site_packages,
)
from .utils import resolve_package_metadata
from ..pack.installers import build_installer
from ..pack.utils import cleanup_dist


def cmd_package(args: argparse.Namespace) -> int:
    script_path = args.script
    if not script_path:
        script_path = "app.py"

    script = Path(script_path)
    # Resolve script path early for reliable relative lookups
    script = script.resolve()
    if not script.exists():
        log(f"Script not found: {script}", style="error")
        return 1

    console.print(Rule("[bold cyan]Pytron Builder"))

    progress = get_progress()
    task = progress.add_task("Starting...", total=100)
    progress.start()

    # If the user provided a .spec file, use it directly
    if script.suffix == ".spec":
        log(f"Packaging using spec file: {script}")
        progress.update(task, description="Building from Spec...", completed=10)
        # When using a spec file, most other arguments are ignored by PyInstaller
        # as the spec file contains the configuration.
        # Prepare and optionally generate hooks from the current venv so PyInstaller
        # includes missing dynamic imports/binaries. Only generate hooks if user
        # requested via CLI flags (`--collect-all` or `--force-hooks`).
        temp_hooks_dir = None
        env = None
        try:
            if getattr(args, "collect_all", False) or getattr(
                args, "force_hooks", False
            ):
                temp_hooks_dir = script.parent / "build" / "nuclear_hooks"
                collect_mode = getattr(args, "collect_all", False)

                # Get venv site-packages to ensure we harvest the correct environment
                python_exe = get_python_executable()
                site_packages = get_venv_site_packages(python_exe)

                generate_nuclear_hooks(
                    temp_hooks_dir,
                    collect_all_mode=collect_mode,
                    search_path=site_packages,
                )
        except Exception as e:
            log(f"Warning: failed to generate nuclear hooks: {e}", style="warning")

        cmd = [get_python_executable(), "-m", "PyInstaller"]
        cmd.append(str(script))
        cmd.append("--noconfirm")

        log(f"Running: {' '.join(cmd)}", style="dim")

        if env is not None:
            ret_code = run_command_with_output(cmd, env=env, style="dim")
        else:
            ret_code = run_command_with_output(cmd, style="dim")

        # Cleanup
        if ret_code == 0:
            out_name = args.name or script.stem
            cleanup_dist(Path("dist") / out_name)

        # If installer was requested, we still try to build it
        if ret_code == 0 and args.installer:
            progress.update(task, description="Building Installer...", completed=80)
            out_name = args.name or script.stem
            ret_code = build_installer(out_name, script.parent, args.icon)

        progress.update(task, description="Done!", completed=100)
        progress.stop()
        if ret_code == 0:
            console.print(Rule("[bold green]Success"))
            log(f"App packaged successfully: dist/{out_name}", style="bold green")
        return ret_code

    # Resolve output name and load settings
    out_name, settings = resolve_package_metadata(script, args.name)

    # --- Modular Build Pipeline ---
    from ..pack.pipeline import BuildContext, Pipeline
    from ..pack.modules import (
        FrontendModule,
        AssetModule,
        PackModule,
        EngineModule,
        MetadataModule,
        InstallerModule,
        PluginModule,
        HookModule,
        IconModule,
    )

    # Resolve icon to absolute path NOW (before CWD can drift during post_build)
    resolved_icon = None
    if args.icon:
        icon_path = Path(args.icon)
        if not icon_path.is_absolute():
            icon_path = (script.parent / icon_path).resolve()
        resolved_icon = str(icon_path) if icon_path.exists() else args.icon

    # Initialize Context
    ctx = BuildContext(
        script=script,
        out_name=out_name,
        app_icon=resolved_icon,
        settings=settings,
        engine=args.engine or ("chrome" if args.chrome else None),
        is_secure=args.secure,
        is_nuitka=args.nuitka,
        is_onefile=args.one_file,
        is_archive_only=getattr(args, "archive_only", False),
        progress=progress,
        task_id=task,
    )

    # Pass through some CLI flags to context for module use
    ctx.smart_assets = args.smart_assets
    ctx.build_installer = args.installer
    ctx.bundled = args.bundled
    ctx.collect_all = getattr(args, "collect_all", False)
    ctx.force_hooks = getattr(args, "force_hooks", False)
    ctx.add_data = args.add_data or []
    ctx.extra_args = getattr(args, "extra_args", [])

    # --- Crystal Integrity Check ---
    if getattr(args, "crystal", False):
        from ..pack.crystal import AppAuditor

        auditor = AppAuditor(script)
        log(f"Running Crystal Integrity Check on {script}...", style="cyan")

        # Run the audit (this generates requirements.lock.json)
        manifest = auditor.run_audit()

        if manifest:
            # Inject discovered modules as hidden imports for the builder
            discovered_modules = manifest.get("modules", [])
            log(
                f"Crystal detected {len(discovered_modules)} hidden dependencies.",
                style="green",
            )

            current_hidden = settings.get("hidden_imports", [])
            # Merge unique items
            settings["hidden_imports"] = list(set(current_hidden + discovered_modules))

            # Also ensure data files are tracked if needed (future expansion)
            # data_files = manifest.get("files", [])

    # Initialize Pipeline
    pipeline = Pipeline(ctx)

    # Add Modules
    pipeline.add_module(FrontendModule())
    pipeline.add_module(IconModule())
    pipeline.add_module(AssetModule())

    if getattr(args, "pack", False) or getattr(args, "archive_only", False):
        pipeline.add_module(PackModule())

    pipeline.add_module(HookModule())
    pipeline.add_module(EngineModule())
    pipeline.add_module(
        PluginModule()
    )  # Important: Plugin module handles custom add_data

    if args.secure and ctx.engine != "rust":
        from ..pack.secure import SecurityModule

        pipeline.add_module(SecurityModule())

    if args.fortress:
        try:
            from fortress import FortressModule

            pipeline.add_module(
                FortressModule(
                    use_cython=not args.no_cython,
                    use_optimization=not args.no_shake,
                    patch_from=args.patch_from,
                )
            )
            log("Fortress Architecture enabled.", style="cyan")
        except ImportError:
            log(
                "Error: 'pytron-fortress' package not found. Run 'pip install -e pytron-suite/fortress' to use this feature.",
                style="error",
            )
            return 1

    pipeline.add_module(MetadataModule())
    pipeline.add_module(InstallerModule())

    # Run Pipeline with Core Compiler
    if getattr(args, "archive_only", False):

        def run_archive_only_build(context: BuildContext):
            log("Packaging in Archive-Only Mode...", style="info")
            context.progress.update(
                context.task_id, description="Generating app.pytron...", completed=50
            )

            # Ensure dist directory exists
            context.dist_dir.mkdir(parents=True, exist_ok=True)

            archive_path = context.build_dir / "app.pytron"
            if not archive_path.exists():
                log(
                    "Error: app.pytron was not found in the build folder.",
                    style="error",
                )
                return 1

            dest_path = context.dist_dir / "app.pytron"
            import shutil

            shutil.copy2(archive_path, dest_path)
            log(f"Archive written to: {dest_path}", style="success")

            # Copy settings.json to dist directory too, so the runner can read it without opening zip
            settings_dest = context.dist_dir / "settings.json"
            import json

            settings_dest.write_text(json.dumps(context.settings, indent=4))
            log(f"Settings metadata written to: {settings_dest}", style="dim")

            context.progress.update(context.task_id, description="Done!", completed=100)
            return 0

        ret_code = pipeline.run(run_archive_only_build)
    elif ctx.engine == "rust":
        from ..pack.rust_engine import RustEngine

        rust_engine = RustEngine()
        # Rust Engine handles the entire build process natively
        ret_code = pipeline.run(rust_engine.build)

    elif args.nuitka:
        from ..pack.nuitka import run_nuitka_build

        # TODO: Refactor Nuitka to use BuildContext too for full parity
        # For now, we'll call it with a compatible shim if possible or just original args
        # But let's prioritize PyInstaller for this refactor
        ret_code = pipeline.run(run_nuitka_build)
    else:
        from ..pack.pyinstaller import run_pyinstaller_build

        ret_code = pipeline.run(run_pyinstaller_build)

    progress.stop()
    if ret_code == 0:
        console.print(Rule("[bold green]Success"))
        if getattr(args, "archive_only", False):
            log(
                f"App archive packaged successfully: dist/{ctx.out_name}/app.pytron",
                style="bold green",
            )
        else:
            log(f"App packaged successfully: dist/{ctx.out_name}", style="bold green")
    return ret_code
