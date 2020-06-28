'''
Manage XBPS packages and repositories. Note that XBPS package names are case-sensitive.
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def upgrade(state, host):
    '''
    Upgrades all XBPS packages.
    '''

    yield 'xbps-install -y -u'

_upgrade = upgrade  # noqa: E305


@operation
def update(state, host):
    '''
    Update XBPS repositories.
    '''

    yield 'xbps-install -S'

_update = update  # noqa: E305


@operation
def packages(
    state, host,
    packages=None, present=True,
    update=False, upgrade=False,
):
    '''
    Install/remove/update XBPS packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed

    Example:

    .. code:: python

        xbps.packages(
            {'Install Vim and Vim Pager'},
            ['vimpager', 'vim'],
        )

    '''

    if update:
        yield _update(state, host)

    if upgrade:
        yield _upgrade(state, host)

    yield ensure_packages(
        packages, host.fact.xbps_packages, present,
        install_command='xbps-install -y -u',
        uninstall_command='xbps-remove -y',
    )
