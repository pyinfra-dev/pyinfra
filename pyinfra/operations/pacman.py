'''
Manage pacman packages. (Arch Linux package manager)
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def upgrade(state, host):
    '''
    Upgrades all pacman packages.
    '''

    yield 'pacman --noconfirm -Su'

_upgrade = upgrade  # noqa: E305


@operation
def update(state, host):
    '''
    Updates pacman repositories.
    '''

    yield 'pacman -Sy'

_update = update  # noqa: E305


@operation
def packages(
    state, host,
    packages=None, present=True,
    update=False, upgrade=False,
):
    '''
    Add/remove pacman packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + update: run pacman -Sy before installing packages
    + upgrade: run pacman -Syu before installing packages

    Versions:
        Package versions can be pinned like pacman: ``<pkg>=<version>``.

    Example:

    .. code:: python

        pacman.packages(
            {'Install Vim and a plugin'},
            ['vim-fugitive', 'vim'],
            update=True,
        )
    '''

    if update:
        yield _update(state, host)

    if upgrade:
        yield _upgrade(state, host)

    yield ensure_packages(
        packages, host.fact.pacman_packages, present,
        install_command='pacman --noconfirm -S',
        uninstall_command='pacman --noconfirm -R',
    )
