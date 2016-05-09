# pyinfra
# File: pyinfra/modules/pip.py
# Desc: manage pip packages

'''
Manage pip packages. Compatible globally or inside a virtualenv.
'''

from __future__ import unicode_literals

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def packages(
    state, host,
    packages=None, present=True, latest=False,
    requirements=None, virtualenv=None
):
    '''
    Manage pip packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + requirements: location of requirements file to install
    + virtualenv: root directory of virtualenv to work in

    Versions:
        Package versions can be pinned like pip: ``<pkg>==<version>``
    '''

    commands = []

    if requirements is not None:
        commands.append('pip install -r {0}'.format(requirements))

    current_packages = (
        host.fact.pip_virtualenv_packages(virtualenv)
        if virtualenv else host.fact.pip_packages
    )

    commands.extend(ensure_packages(
        packages, current_packages, present,
        install_command='pip install',
        uninstall_command='pip uninstall',
        version_join='==',
        upgrade_command='pip install --upgrade',
        latest=latest,
    ))

    # Wrap commands inside virtualenv when present
    if virtualenv:
        virtualenv = virtualenv.rstrip('/')
        commands = [
            '{0}/bin/{1}'.format(virtualenv, command)
            for command in commands
        ]

    return commands
