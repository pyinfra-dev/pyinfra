try:
    from pkg_resources import get_distribution
    __version__ = get_distribution('pyinfra').version
except Exception:
    __version__ = 'unknown'
