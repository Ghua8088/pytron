
# Android Development Guide

## 1. Open in Android Studio
1. Launch **Android Studio**.
2. Select **Open**.
3. Navigate to: `D:\playground\pytron\pytron\platforms\android\shell`.
4. Click **OK**.

## 2. Sync Gradle
Android Studio should automatically detect the `build.gradle` files.
- If you see a banner "Gradle files have changed since last project sync...", click **Sync Now**.
- Wait for the sync to complete. It will download dependencies and configure the C++ build.

## 3. Python Assets (Critical!)
The app expects a Python environment in `assets/python`.
Currently, I have created a sample `main.py` there.
**However**, for a real app, you must bundle the Python Standard Library.
1. Copy the **Lib** folder from your Python 3.14 installation.
2. Paste it into: `pytron/platforms/android/shell/app/src/main/assets/python/Lib`.
   (Or zip it as `python314.zip` and handle unzipping in Java/Kotlin, but for now raw files are easier).

## 4. Build & Run
1. Connect an Android device (with USB Debugging on) or create an Emulator.
2. Select the **app** configuration in the toolbar.
3. Click the green **Play (Run)** button.

## Troubleshooting
- **"libpython3.14.so not found"**: Ensure the ABI folder in `src/main/jnilibs` matches your device (e.g., `arm64-v8a`).
- **Python Crash**: Check Logcat (filter for "Pytron"). If Python standard library is missing, imports like `os` or `json` might fail if they aren't built-in.
