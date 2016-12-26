# pyinfra
# File: pyinfra/modules/pip.py
# Desc: manage pip packages

'''
Manage pip packages. Compatible globally or inside a virtualenv.
'''

from __future__ import unicode_literals

from pyinfra.api import operation
from pyinfra.modules import files

from .util.packaging import ensure_packages


@operation
def virtualenv(
    state, host, path,
    python=None, site_packages=False, always_copy=False, present=True,
):
    '''
    Manage virtualenv.

    + python: python interpreter to use
    + site_packages: give access to the global site-packages
    + always_copy: always copy files rather than symlinking
    + present: whether the virtualenv should exist
    '''

    if present is False and host.fact.directory(path):
        yield files.directory(state, host, path, present=False)

    elif present and not host.fact.directory(path):
        # Create missing virtualenv
        command = ['virtualenv']

        if python:
            command.append('-p {0}'.format(python))

        if site_packages:
            command.append('--system-site-packages')

        if always_copy:
            command.append('--always-copy')

        command.append(path)

        yield ' '.join(command)

_virtualenv = virtualenv


@operation
def packages(
    state, host,
    packages=None, present=True, latest=False,
    requirements=None, pip='pip', virtualenv=None, virtualenv_kwargs=None,
):
    '''
    Manage pip packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + requirements: location of requirements file to install
    + pip: name or path of the pip directory to use
    + virtualenv: root directory of virtualenv to work in
    + virtualenv_kwargs: dictionary of arguments to pass to ``pip.virtualenv``

    Virtualenv:
        This will be created if it does not exist already. Use
        ``virtualenv_kwargs`` from the virtualenv operation to control this.

    Versions:
        Package versions can be pinned like pip: ``<pkg>==<version>``
    '''

    virtualenv_kwargs = virtualenv_kwargs or {}

    if requirements is not None:
        yield '{0} install -r {1}'.format(pip, requirements)

    current_packages = host.fact.pip_packages(virtualenv)

    # Ensure any virutalenv
    if virtualenv:
        yield _virtualenv(state, host, virtualenv, **virtualenv_kwargs)

    install_command = (
        '{0} install'.format(pip)
        if virtualenv is None
        else '{0}/bin/pip install'.format(virtualenv)
    )

    uninstall_command = (
        '{0} uninstall'.format(pip)
        if virtualenv is None
        else '{0}/bin/pip uninstall'.format(virtualenv)
    )

    upgrade_command = (
        '{0} install --upgrade'.format(pip)
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
