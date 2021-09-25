'''
Manage pkgin packages.
'''

from pyinfra.api import operation
from pyinfra.facts.pkgin import PkginPackages

from .util.packaging import ensure_packages


@operation
def upgrade(state=None, host=None):
    '''
    Upgrades all pkgin packages.
    '''

    yield 'pkgin -y upgrade'

_upgrade = upgrade  # noqa: E305


@operation
def update(state=None, host=None):
    '''
    Updates pkgin repositories.
    '''

    yield 'pkgin -y update'

_update = update  # noqa: E305


@operation
def packages(
    packages=None, present=True, latest=False,
    update=False, upgrade=False,
    state=None, host=None,
):
    '''
    Add/remove/update pkgin packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run ``pkgin update`` before installing packages
    + upgrade: run ``pkgin upgrade`` before installing packages

    Examples:

    .. code:: python

        # Update package list and install packages
        pkgin.packages(
            name='Install tmux and Vim',
            packages=['tmux', 'vim'],
            update=True,
        )

        # Install the latest versions of packages (always check)
        pkgin.packages(
            name='Install latest Vim',
            packages=['vim'],
            latest=True,
        )
    '''

    if update:
        yield _update(state=state, host=host)

    if upgrade:
        yield _upgrade(state=state, host=host)

    # TODO support glob for specific versions (it isn't as simple
    # as apt's, as pkgin supports something like 'mysql-server>=5.6<5.7')
    yield ensure_packages(
        host, packages, host.get_fact(PkginPackages), present,
        install_command='pkgin -y install',
        uninstall_command='pkgin -y remove',
        upgrade_command='pkgin -y upgrade',
        latest=latest,
    )
