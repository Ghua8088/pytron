try:
    from pytron.dependencies import pytron_os
    print("pytron_os is available")
    print(f"Functions: {dir(pytron_os)}")
except ImportError as e:
    print(f"pytron_os NOT available: {e}")
except Exception as e:
    print(f"Error checking pytron_os: {e}")
