"""
Manage pacman packages. (Arch Linux package manager)
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.pacman import (
    PacmanHeldPackages,
    PacmanPackages,
    PacmanUnpackGroup,
    PacmanUpgradeablePackages,
)
from pyinfra.facts.util.packages import build_package_map

from .util.packaging import ensure_packages


def _name_only_format(name: str, operator: str, version: str) -> str:
    """Format function that strips the version — pacman does not support version pinning."""
    return name


@operation()
def upgrade():
    """
    Upgrades all pacman packages.

    This operation is idempotent: it checks for available upgrades first
    and only runs ``pacman -Su`` when upgradeable packages exist.
    """

    upgradeable = host.get_fact(PacmanUpgradeablePackages)
    if not upgradeable:
        host.noop("all packages are up to date")
        return

    yield "pacman --noconfirm -Su"


_upgrade = upgrade._inner  # noqa: E305


@operation(is_idempotent=False)
def update():
    """
    Updates pacman repositories.
    """

    yield "pacman -Sy"


_update = update._inner  # noqa: E305


@operation()
def packages(
    packages: str | list[str] | None = None,
    present=True,
    update=False,
    upgrade=False,
    latest=False,
):
    """
    Add/remove pacman packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + update: run ``pacman -Sy`` before installing packages
    + upgrade: run ``pacman -Su`` before installing packages
    + latest: upgrade installed packages that have available updates

    Versions:
        Package versions can be pinned like pacman: ``<pkg>=<version>``.
        The version is used to **check** the installed state; the install
        command does not include the version because pacman does not support
        version pinning on install.

    **Example:**

    .. code:: python

        from pyinfra.operations import pacman
        pacman.packages(
            name="Install Vim and a plugin",
            packages=["vim-fugitive", "vim"],
            update=True,
        )
    """

    if update:
        yield from _update()

    if upgrade:
        yield from _upgrade()

    installed = host.get_fact(PacmanPackages)
    upgradeable = host.get_fact(PacmanUpgradeablePackages)
    held = host.get_fact(PacmanHeldPackages)

    current_packages = build_package_map(installed, upgradeable, set(held))

    yield from ensure_packages(
        host,
        packages,
        current_packages,
        present,
        install_command="pacman --noconfirm -S",
        uninstall_command="pacman --noconfirm -R",
        latest=latest,
        upgrade_command="pacman --noconfirm -S",
        expand_package_fact=lambda package: host.get_fact(PacmanUnpackGroup, package=package),
        version_join="=",
        inst_vers_format_fn=_name_only_format,
    )
