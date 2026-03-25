import sys

if sys.platform == "win32":
    from .windows import WindowsImplementation
elif sys.platform.startswith("linux"):
    from .linux import LinuxImplementation
elif sys.platform == "darwin":
    from .darwin import DarwinImplementation as MacOSImplementation
else:
    # Generic or unsupported platform fallback
    from .interface import PlatformInterface as WindowsImplementation
    from .interface import PlatformInterface as LinuxImplementation
    from .interface import PlatformInterface as MacOSImplementation

__all__ = ["WindowsImplementation", "LinuxImplementation", "MacOSImplementation"]
