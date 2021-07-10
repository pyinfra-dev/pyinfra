'''
Manage Ruby gem packages. (see https://rubygems.org/ )
'''

from pyinfra.api import operation
from pyinfra.facts.gem import GemPackages

from .util.packaging import ensure_packages


@operation
def packages(packages=None, present=True, latest=False, state=None, host=None):
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
            name='Install rspec',
            packages=['rspec'],
        )
    '''

    yield ensure_packages(
        host, packages, host.get_fact(GemPackages), present,
        install_command='gem install',
        uninstall_command='gem uninstall',
        upgrade_command='gem update',
        version_join=':',
        latest=latest,
    )
