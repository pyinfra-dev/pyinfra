import importlib


def __getattr__(name):
    try:
        # On-demand import of fact modules, so we don't have to import them all at once
        # this forces py3.7>=, but that's fine as py2 is EOL and py3.6 is also EOL
        # Also, Pyinfra is py3.11>=, so this is not a breaking change.
        return importlib.import_module(f".{name}", __package__)
    except ImportError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# # This file only exists to support:
# # from pyinfra.operations import freebsd
# # freebsd.X.Y
#
# from glob import glob
# from os import path
#
# module_filenames = glob(path.join(path.dirname(__file__), "*.py"))
# module_names = [path.basename(name)[:-3] for name in module_filenames]
# __all__ = [name for name in module_names if name != "__init__"]
#
# from . import *  # noqa
