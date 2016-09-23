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

    if requirements is not None:
        yield 'pip install -r {0}'.format(requirements)

    current_packages = host.fact.pip_packages(virtualenv)

    if virtualenv:
        virtualenv = virtualenv.rstrip('/')

    install_command = (
        'pip install'
        if virtualenv is None
        else '{0}/bin/pip install'.format(virtualenv)
    )

    uninstall_command = (
        'pip uninstall'
        if virtualenv is None
        else '{0}/bin/pip uninstall'.format(virtualenv)
    )

    upgrade_command = (
        'pip install --upgrade'
        if virtualenv is None
        else '{0}/bin/pip install --upgrade'.format(virtualenv)
    )

    yield ensure_packages(
        packages, current_packages, present,
        install_command=install_command,
        uninstall_command=uninstall_command,
        upgrade_command=upgrade_command,
        version_join='==',
        latest=latest,
    )
