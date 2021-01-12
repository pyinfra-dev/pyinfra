'''
Manage pacman packages. (Arch Linux package manager)
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def upgrade(state=None, host=None):
    '''
    Upgrades all pacman packages.
    '''

    yield 'pacman --noconfirm -Su'

_upgrade = upgrade  # noqa: E305


@operation
def update(state=None, host=None):
    '''
    Updates pacman repositories.
    '''

    yield 'pacman -Sy'

_update = update  # noqa: E305


@operation
def packages(
    packages=None, present=True,
    update=False, upgrade=False,
    state=None, host=None,
):
    '''
    Add/remove pacman packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + update: run ``pacman -Sy`` before installing packages
    + upgrade: run ``pacman -Su`` before installing packages

    Versions:
        Package versions can be pinned like pacman: ``<pkg>=<version>``.

    Example:

    .. code:: python

        pacman.packages(
            name='Install Vim and a plugin',
            packages=['vim-fugitive', 'vim'],
            update=True,
        )
    '''

    if update:
        yield _update(state=state, host=host)

    if upgrade:
        yield _upgrade(state=state, host=host)

    yield ensure_packages(
        host, packages, host.fact.pacman_packages, present,
        install_command='pacman --noconfirm -S',
        uninstall_command='pacman --noconfirm -R',
        lower=False,
        expand_package_fact=host.fact.pacman_unpack_group,
    )
