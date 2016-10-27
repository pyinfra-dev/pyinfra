# pyinfra
# File: pyinfra/modules/pip.py
# Desc: manage virtualenvs

'''
Manage Python virtual environments
'''

from __future__ import unicode_literals

from pyinfra.api import operation
from pyinfra.modules import files


@operation
def virtualenv(
    state, host,
    path, python='python3', site_packages=False, always_copy=False,
    present=True,
):
    '''
    Manage virtualenv.

    + python: python interpreter to use
    + site_packages: give access to the global site-packages
    + always_copy: always copy files rather than symlinking
    + present: whether the virtualenv should be installed
    '''

    if present is False and host.fact.directory(path):
        # Ensure deletion of unwanted virtualenv
        yield from files.directory(state, host, path, present=False)

    elif present and not host.fact.directory(path):
        # Create missing virtualenv
        command = '/usr/bin/virtualenv -p {}'.format(python)
        if site_packages:
            command += ' --system-site-packages'
        if always_copy:
            command += ' --always-copy'
        command += ' ' + path
        yield command
