# pyinfra
# File: pyinfra/modules/pip.py
# Desc: manage pip packages

'''
Manage pip packages. Compatible globally or inside a virtualenv.
'''

from pyinfra.api import operation


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
    '''

    if packages is None:
        packages = []

    if isinstance(packages, basestring):
        packages = [packages]

    # pip packages are case-insensitive & interchange -, _
    packages = [
        package.lower().replace('_', '-')
        for package in packages
    ]

    commands = []

    if requirements is not None:
        commands.append('pip install -r {0}'.format(requirements))

    current_packages = (
        host.pip_packages_virtualenv(virtualenv)
        if virtualenv else host.pip_packages
    )

    # Don't fail if pip isn't found as it's not a system package manager
    current_packages = current_packages or {}

    if present is True:
        diff_packages = [
            package for package in packages
            if package not in current_packages
        ]

        if diff_packages:
            commands.append('pip install {0}'.format(' '.join(diff_packages)))

    else:
        diff_packages = [
            package for package in packages
            if package in current_packages
        ]

        if diff_packages:
            commands.append('pip uninstall {0}'.format(' '.join(diff_packages)))

    if virtualenv:
        # Remove any trailing slash
        virtualenv = virtualenv.rstrip('/')
        commands = [
            '{0}/bin/{1}'.format(virtualenv, command)
            for command in commands
        ]

    return commands
