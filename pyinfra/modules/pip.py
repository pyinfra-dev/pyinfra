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
    Manage Python virtualenvs.

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

_virtualenv = virtualenv  # noqa


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
        This will be created if it does not exist already. ``virtualenv_kwargs``
        will be passed to ``pip.virtualenv`` which can be used to control how
        the env is created.

    Versions:
        Package versions can be pinned like pip: ``<pkg>==<version>``.
    '''

    virtualenv_kwargs = virtualenv_kwargs or {}

    # Ensure any virutalenv
    if virtualenv:
        yield _virtualenv(state, host, virtualenv, **virtualenv_kwargs)

        # And update pip path
        virtualenv = virtualenv.rstrip('/')
        pip = '{0}/bin/{1}'.format(virtualenv, pip)

    # Install requirements
    if requirements is not None:
        yield '{0} install -r {1}'.format(pip, requirements)

    # Handle passed in packages
    if packages:
        current_packages = host.fact.pip_packages(pip)

        yield ensure_packages(
            packages, current_packages, present,
            install_command='{0} install'.format(pip),
            uninstall_command='{0} uninstall'.format(pip),
            upgrade_command='{0} install --upgrade'.format(pip),
            version_join='==',
            latest=latest,
        )
