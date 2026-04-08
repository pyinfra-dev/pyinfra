import importlib
from glob import glob
from os import path

_module_filenames = glob(path.join(path.dirname(__file__), "*.py"))
__all__ = sorted(
    set(path.basename(name)[:-3] for name in _module_filenames if not name.endswith("__init__.py"))
)


def __getattr__(name):
    # On-demand import of operations modules, so we don't have to import them all at once
    # this forces py3.7>=, but that's fine as py2 is EOL and py3.6 is also EOL
    # Also, Pyinfra is py3.11>=, so this is not a breaking change.
    if name in __all__:
        return importlib.import_module(f".{name}", __package__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return __all__
