'''
Manage Ruby gem packages. (see https://rubygems.org/ )
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def packages(state, host, packages=None, present=True, latest=False):
    '''
    Add/remove/update gem packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version

    Versions:
        Package versions can be pinned like gem: ``<pkg>:<version>``.

    Example:

    .. code:: python

        # Note: Assumes that 'gem' is installed.
        gem.packages(
            {'Install rspec'},
            'rspec',
        )
    '''

    yield ensure_packages(
        packages, host.fact.gem_packages, present,
        install_command='gem install',
        uninstall_command='gem uninstall',
        upgrade_command='gem update',
        version_join=':',
        latest=latest,
    )
