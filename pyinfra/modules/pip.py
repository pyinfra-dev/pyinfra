# pyinfra
# File: pyinfra/modules/pip.py
# Desc: manage pip packages

'''
Manage pip packages. Compatible globally or inside a virtualenv.

Uses:

+ `pip`
'''

from pyinfra import host
from pyinfra.api import operation


@operation
def packages(packages=None, present=True, requirements=None, venv=None):
    '''
    Manage pip packages.

    # venv: a virtualenv root directory
    '''
    if packages is None:
        packages = []

    # pip packages are case-insensitive
    packages = [package.lower() for package in packages]

    commands = []

    if requirements is not None:
        commands.append('pip install -r {0}'.format(requirements))

    current_packages = host.venv_pip_packages(venv) if venv else host.pip_packages
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

    if venv:
        # Remove any trailing slash
        venv = venv.rstrip('/')
        commands = [
            '{0}/bin/{1}'.format(venv, command)
            for command in commands
        ]

    return commands
