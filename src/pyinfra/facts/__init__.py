import importlib
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
        deb,
        dnf,
        docker,
        efibootmgr,
        files,
        flatpak,
        freebsd,
        gem,
        git,
        gpg,
        hardware,
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
        podman,
        postgres,
        postgresql,
        rpm,
        runit,
        selinux,
        server,
        snap,
        systemd,
        sysvinit,
        upstart,
        vzctl,
        xbps,
        yum,
        zfs,
        zypper,
    )

__all__ = [
    "apk",
    "apt",
    "brew",
    "bsdinit",
    "cargo",
    "choco",
    "crontab",
    "deb",
    "dnf",
    "docker",
    "efibootmgr",
    "files",
    "flatpak",
    "freebsd",
    "gem",
    "git",
    "gpg",
    "hardware",
    "iptables",
    "launchd",
    "lxd",
    "mysql",
    "npm",
    "openrc",
    "opkg",
    "pacman",
    "pip",
    "pipx",
    "pkgin",
    "pkg",
    "podman",
    "postgres",
    "postgresql",
    "rpm",
    "runit",
    "selinux",
    "server",
    "snap",
    "systemd",
    "sysvinit",
    "upstart",
    "vzctl",
    "xbps",
    "yum",
    "zfs",
    "zypper",
]


def __getattr__(name):
    # On-demand import of operations modules, so we don't have to import them all at once
    # this forces py3.7>=, but that's fine as py2 is EOL and py3.6 is also EOL
    # Also, Pyinfra is py3.11>=, so this is not a breaking change.
    if name in __all__:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return __all__


# # This file only exists to support:
# # from pyinfra import operations
# # operations.X.Y
#
# from glob import glob
# from os import path
#
# module_filenames = glob(path.join(path.dirname(__file__), "*.py"))
# module_names = [path.basename(name)[:-3] for name in module_filenames]
# __all__ = [name for name in module_names if name != "__init__"]
#
# from . import *  # noqa
