"""
Manage XBPS packages and repositories. Note that XBPS package names are case-sensitive.
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.xbps import XbpsPackages, XbpsSelfUpdate

from .util.packaging import ensure_packages

# XBPS won't install or update anything else while an update to itself is pending
_SELF_UPDATE_COMMAND = "xbps-install -y -u xbps"


@operation(is_idempotent=False)
def upgrade():
    """
    Upgrades all XBPS packages, updating ``xbps`` itself first.
    """

    yield _SELF_UPDATE_COMMAND
    yield "xbps-install -y -u"


_upgrade = upgrade._inner  # noqa: E305


@operation(is_idempotent=False)
def update():
    """
    Update XBPS repositories.
    """

    yield "xbps-install -S"


_update = update._inner  # noqa: E305


@operation()
def packages(
    packages: str | list[str] | None = None,
    present=True,
    update=False,
    upgrade=False,
):
    """
    Install/remove/update XBPS packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + update: run ``xbps-install -S`` before installing packages
    + upgrade: run ``xbps-install -y -u`` before installing packages

    If ``xbps`` itself has an update available it is updated before installing
    packages, as XBPS refuses to install anything else until it has.

    **Example:**

    .. code:: python

        from pyinfra.operations import xbps
        xbps.packages(
            name="Install Vim and Vim Pager",
            packages=["vimpager", "vim"],
        )

    """

    if update:
        yield from _update()

    if upgrade:
        yield from _upgrade()

    commands = list(
        ensure_packages(
            host,
            packages,
            host.get_fact(XbpsPackages),
            present,
            install_command="xbps-install -y -u",
            uninstall_command="xbps-remove -y",
        )
    )

    # Upgrading has already updated xbps. Otherwise, after syncing the fact is
    # out of date, so update xbps regardless (it does nothing when up to date).
    if commands and present and not upgrade:
        self_update: list[str] = host.get_fact(XbpsSelfUpdate)
        if update or any(self_update):
            yield _SELF_UPDATE_COMMAND

    yield from commands
