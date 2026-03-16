Platforms

Responsibilities
- Provide OS-specific helpers for windows, macOS, linux, and android (tray, dialogs, window flags).
- Expose platform ops used by `Webview` and `App`.

Key locations
- [pytron/platforms](pytron/platforms)
- Android builder: [pytron/platforms/android/builder.py](pytron/platforms/android/builder.py)

Interactions
- `Webview` loads platform helpers at runtime to apply native tweaks.
- CLI `android` flows call into Android ops and the AndroidBuilder to prepare AAB/APKs.