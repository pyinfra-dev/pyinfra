# pyinfra
# File: pyinfra/modules/gem.py
# Desc: manage gem packages

'''
Mange gem packages.
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def packages(state, host, packages=None, present=True, latest=False):
    '''
    Manage gem packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version

    Versions:
        Package versions can be pinned like gem: ``<pkg>:<version>``
    '''

    return ensure_packages(
        packages, host.fact.gem_packages, present,
        install_command='gem instal',
        uninstall_command='gem uninstall',
        version_join=':',
        upgrade_command='gem update',
        latest=latest
    )
