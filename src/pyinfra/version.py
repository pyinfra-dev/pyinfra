try:
    try:
        from importlib_metadata import version
    except ImportError:
        from importlib.metadata import version

    __version__ = version("pyinfra")
except Exception:
    __version__ = "unknown"
