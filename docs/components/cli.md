CLI

Responsibilities
- Parse user commands and dispatch to modular `commands/*` implementations.
- Provide convenience flags for packaging, engines, frontend builds, and Android.

Key files
- [pytron/cli.py](pytron/cli.py)
- [pytron/commands](pytron/commands)

Interactions
- CLI calls build/run workflows which create `App` instances or invoke `pack` pipeline modules.
- The `android` subcommand delegates to platform/android ops and the Android builder.