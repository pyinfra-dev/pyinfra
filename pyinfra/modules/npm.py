'''
Manage npm (aka node aka Node.js) packages.
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def packages(state, host, packages=None, present=True, latest=False, directory=None):
    '''
    Install/remove/update npm packages.

    + packages: list of packages to ensure
    + present: whether the packages should be present
    + latest: whether to upgrade packages without a specified version
    + directory: directory to manage packages for, defaults to global

    Versions:
        Package versions can be pinned like npm: ``<pkg>@<version>``.
    '''

    current_packages = host.fact.npm_packages(directory)

    install_command = (
        'npm install -g'
        if directory is None
        else 'cd {0} && npm install'.format(directory)
    )

    uninstall_command = (
        'npm uninstall -g'
        if directory is None
        else 'cd {0} && npm uninstall'.format(directory)
    )

    upgrade_command = (
        'npm update -g'
        if directory is None
        else 'cd {0} && npm update'.format(directory)
    )

    yield ensure_packages(
        packages, current_packages, present,
        install_command=install_command,
        uninstall_command=uninstall_command,
        upgrade_command=upgrade_command,
        version_join='@',
        latest=latest,
    )
