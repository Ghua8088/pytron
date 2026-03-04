import sys
import os

dep_path = os.path.abspath(os.path.join(os.getcwd(), "pytron", "dependencies"))
print(f"Checking Dependencies at: {dep_path}")
sys.path.append(dep_path)

try:
    import pytron_native

    print(" SUCCESS: pytron_native imported!")
except ImportError as e:
    print(f" FAILURE: {e}")
except Exception as e:
    print(f" ERROR: {e}")
