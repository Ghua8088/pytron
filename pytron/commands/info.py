import argparse
import sys

def cmd_info(args: argparse.Namespace) -> int:
    try:
        from pytron import __version__  # type: ignore
    except Exception:
        __version__ = None

    print('Pytron CLI')
    if __version__:
        print(f'Version: {__version__}')
    print(f'Python: {sys.version.splitlines()[0]}')
    print(f'Platform: {sys.platform}')
    return 0
