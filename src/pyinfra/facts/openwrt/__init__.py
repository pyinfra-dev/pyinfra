import importlib

ALL = {
    "OpenWrtFeature": "features.OpenWrtFeature",
    "OpenWrtHasFeature": "features.OpenWrtHasFeature",
    "opkg": "opkg",
}

__all__ = list(ALL.keys())


def __getattr__(name):
    # On-demand import of OpenWrt facts, so we don't have to import them all at once
    # this forces py3.7>=, but that's fine as py2 is EOL and py3.6 is also EOL
    # Also, Pyinfra is py3.11>=, so this is not a breaking change.
    if name in __all__:
        pieces = ALL[name].split(".")
        module = importlib.import_module(f".{pieces[0]}", package=__name__)
        if len(pieces) > 1:
            return getattr(module, pieces[1])
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
