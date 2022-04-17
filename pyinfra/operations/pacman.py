"""
Manage pacman packages. (Arch Linux package manager)
"""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.pacman import PacmanPackages, PacmanUnpackGroup

from .util.packaging import ensure_packages


@operation(is_idempotent=False)
def upgrade():
    """
    Upgrades all pacman packages.
    """

    yield "pacman --noconfirm -Su"


_upgrade = upgrade  # noqa: E305


@operation(is_idempotent=False)
def update():
    """
    Updates pacman repositories.
    """

    yield "pacman -Sy"


_update = update  # noqa: E305


@operation
def packages(
    packages=None,
    present=True,
    update=False,
    upgrade=False,
):
    """
    Add/remove pacman packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + update: run ``pacman -Sy`` before installing packages
    + upgrade: run ``pacman -Su`` before installing packages

    Versions:
        Package versions can be pinned like pacman: ``<pkg>=<version>``.

    **Example:**

    .. code:: python

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

    yield from ensure_packages(
        host,
        packages,
        host.get_fact(PacmanPackages),
        present,
        install_command="pacman --noconfirm -S",
        uninstall_command="pacman --noconfirm -R",
        expand_package_fact=lambda package: host.get_fact(
            PacmanUnpackGroup,
            name=package,
        ),
    )
