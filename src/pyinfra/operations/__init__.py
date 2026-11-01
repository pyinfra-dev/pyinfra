import importlib
from pathlib import Path

_module_paths = Path(__file__).parent.glob("*.py")
__all__ = sorted(set(p.stem for p in _module_paths if p.name != "__init__.py"))


def __getattr__(name):
    # On-demand import of operations modules, so we don't have to import them all at once
    # this forces py3.7>=, but that's fine as py2 is EOL and py3.6 is also EOL
    # Also, Pyinfra is py3.11>=, so this is not a breaking change.
    if name in __all__:
        return importlib.import_module(f".{name}", __package__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return __all__
