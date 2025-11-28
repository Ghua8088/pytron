import sys

# Fetch version from installed package metadata to avoid manual updates
try:
    if sys.version_info >= (3, 8):
        from importlib.metadata import version, PackageNotFoundError
    else:
        from importlib_metadata import version, PackageNotFoundError
        
    try:
        __version__ = version("pytron-kit")
    except PackageNotFoundError:
        __version__ = "0.0.0-dev"
except ImportError:
    __version__ = "0.0.0-dev"

from .core import App, Window, get_resource_path
