"""Per-platform spinner-compression strategies for compress-spinner.py.

Each platform has its own module (e.g. spinners/claude.py, spinners/trae.py)
that exports a STRATEGY instance. Use load(name) to fetch one by name.
"""
from importlib import import_module


def load(platform: str):
    """Return the STRATEGY instance from spinners.<platform>.

    Raises ModuleNotFoundError if no module matches the platform name.
    """
    module = import_module(f".{platform}", package=__name__)
    return module.STRATEGY
