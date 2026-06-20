import importlib
import sys

ALL = {
    "freebsd_update": "freebsd_update",
    "pkg": "pkg",
    "service": "service",
    "sysrc": "sysrc",
}

__all__ = list(ALL.keys())


def __getattr__(name):
    # On-demand import of OpenWrt facts, so we don't have to import them all at once
    # this forces py3.7>=, but that's fine as py2 is EOL and py3.6 is also EOL
    # Also, pyinfra is py3.11>=, so this is not a breaking change.
    if name in __all__:
        pieces = ALL[name].split(".")
        module = importlib.import_module(f".{pieces[0]}", package=__name__)
        if len(pieces) < 2:
            return module
        del sys.modules[module.__name__]
        del sys.modules[__name__].__dict__[pieces[0]]
        return getattr(module, pieces[1])

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
