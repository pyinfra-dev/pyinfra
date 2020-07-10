'''
Manage pip (python) packages. Compatible globally or inside
a virtualenv (virtual environment).
'''

from __future__ import unicode_literals

from pyinfra.api import operation

from . import files
from .util.packaging import ensure_packages


@operation
def virtualenv(
    path,
    python=None, venv=False, site_packages=False, always_copy=False, present=True,
    state=None, host=None,
):
    '''
    Add/remove Python virtualenvs.

    + python: python interpreter to use
    + venv: use standard venv module instead of virtualenv
    + site_packages: give access to the global site-packages
    + always_copy: always copy files rather than symlinking
    + present: whether the virtualenv should exist

    Example:

    .. code:: python

        pip.virtualenv(
            name='Create a virtualenv',
            path='/usr/local/bin/venv',
        )
    '''

    # Check for *contents* of a virtualenv, ie don't accept an empty directory
    # as a valid virtualenv but ensure the activate script exists.
    activate_script_path = '{0}/bin/activate'.format(path)

    if present is False and host.fact.file(activate_script_path):
        yield files.directory(path, present=False, state=state, host=host)

    elif present and not host.fact.file(activate_script_path):
        # Create missing virtualenv
        command = ['virtualenv']

        if venv:
            command = [python or 'python', '-m', 'venv']

        if python and not venv:
            command.append('-p {0}'.format(python))

        if site_packages:
            command.append('--system-site-packages')

        if always_copy and not venv:
            command.append('--always-copy')
        elif always_copy and venv:
            command.append('--copies')

        command.append(path)

        yield ' '.join(command)

_virtualenv = virtualenv  # noqa


@operation
def packages(
    packages=None, present=True, latest=False,
    requirements=None, pip='pip', virtualenv=None, virtualenv_kwargs=None,
    state=None, host=None,
):
    '''
    Install/remove/update pip packages.

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

    Example:

    .. code:: python

        pip.packages(
            name='Install pyinfra into a virtualenv',
            packages=['pyinfra'],
            virtualenv='/usr/local/bin/venv',
        )
    '''

    virtualenv_kwargs = virtualenv_kwargs or {}

    # Ensure any virtualenv
    if virtualenv:
        yield _virtualenv(virtualenv, state=state, host=host, **virtualenv_kwargs)

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
            uninstall_command='{0} uninstall --yes'.format(pip),
            upgrade_command='{0} install --upgrade'.format(pip),
            version_join='==',
            latest=latest,
        )
