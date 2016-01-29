# pyinfra
# File: pyinfra/modules/gem.py
# Desc: manage gem packages

'''
Mange gem packages.
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def packages(state, host, packages=None, present=True):
    '''
    Manage gem packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    '''

    return ensure_packages(
        packages, host.gem_packages, present,
        install_command='gem instal',
        uninstall_command='gem uninstall',
        version_join=':'
    )
