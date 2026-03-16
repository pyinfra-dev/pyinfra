import importlib
from glob import glob
from os import path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import (
        apk,
        apt,
        brew,
        bsdinit,
        cargo,
        choco,
        crontab,
        dnf,
        docker,
        files,
        flatpak,
        gem,
        git,
        iptables,
        launchd,
        lxd,
        mysql,
        npm,
        openrc,
        opkg,
        pacman,
        pip,
        pipx,
        pkg,
        pkgin,
        postgres,
        postgresql,
        puppet,
        python,
        runit,
        selinux,
        server,
        snap,
        ssh,
        systemd,
        sysvinit,
        upstart,
        vzctl,
        xbps,
        yum,
        zfs,
        zypper,
    )

# Lazily discover and build __all__
_module_filenames = glob(path.join(path.dirname(__file__), "*.py"))
__all__ = sorted(
    [
        path.basename(name)[:-3]
        for name in _module_filenames
        if not name.endswith("__init__.py")
    ]
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
