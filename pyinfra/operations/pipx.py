'''
Manage pip (python) packages. Compatible globally or inside
a virtualenv (virtual environment).
'''

from __future__ import unicode_literals

from pyinfra.api import operation
from pyinfra.facts.files import File
from pyinfra.facts.pipx import PipxPackages

from . import files
from .util.packaging import ensure_packages


@operation
def packages(
    packages=None, present=True, latest=False,
    pipx='pipx',
    extra_install_args=None,
    state=None, host=None,
):
    '''
    Install/remove/update pipx packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + pipx: name or path of the pipx directory to use
    + extra_install_args: additional arguments to the pipx install command

    Versions:
        Package versions can be pinned like pip: ``<pkg>==<version>``.

    Example:

    .. code:: python

        pipx.packages(
            name='Install pycowsay',
            packages=['pycowsay'],
            latest=True,
        )
    '''


    install_command = [pipx, 'install']
    if extra_install_args:
        install_command.append(extra_install_args)
    install_command = ' '.join(install_command)

    uninstall_command = ' '.join([pipx, 'uninstall'])

    # Handle passed in packages
    if packages:
        current_packages = host.get_fact(PipxPackages, pipx='pipx')

        yield ensure_packages(
            host, packages, current_packages, present,
            install_command=install_command,
            uninstall_command=uninstall_command,
            upgrade_command='{0} upgrade'.format(pipx),
            version_join='==',
            latest=latest,
        )
