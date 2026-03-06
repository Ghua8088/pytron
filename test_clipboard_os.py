from pytron.dependencies import pytron_os
import time

print("Testing Clipboard...")
test_text = f"Pytron Rust Clipboard Test {time.time()}"
success = pytron_os.set_clipboard_text(test_text)
print(f"Set Clipboard: {success}")

if success:
    retrieved = pytron_os.get_clipboard_text()
    print(f"Retrieved: {retrieved}")
    if retrieved == test_text:
        print("SUCCESS: Clipboard match!")
    else:
        print("FAILURE: Clipboard mismatch!")
else:
    print("FAILURE: Could not set clipboard!")
