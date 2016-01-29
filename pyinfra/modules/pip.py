# pyinfra
# File: pyinfra/modules/pip.py
# Desc: manage pip packages

'''
Manage pip packages. Compatible globally or inside a virtualenv.
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def packages(
    state, host,
    packages=None, present=True,
    requirements=None, virtualenv=None
):
    '''
    Manage pip packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + requirements: location of requirements file to install
    + virtualenv: root directory of virtualenv to work in

    Versions:
        Package versions can be pinned like pip: ``<pkg>==<version>``
    '''

    commands = []

    if requirements is not None:
        commands.append('pip install -r {0}'.format(requirements))

    current_packages = (
        host.pip_packages_virtualenv(virtualenv)
        if virtualenv else host.pip_packages
    )

    commands.extend(ensure_packages(
        packages, current_packages, present,
        install_command='pip install',
        uninstall_command='pip uninstall',
        version_join='=='
    ))

    # Wrap commands inside virtualenv when present
    if virtualenv:
        virtualenv = virtualenv.rstrip('/')
        commands = [
            '{0}/bin/{1}'.format(virtualenv, command)
            for command in commands
        ]

    return commands
