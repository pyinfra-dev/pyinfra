# pyinfra
# File: pyinfra/facts/pip.py
# Desc: facts for the pip package manager

import re

from pyinfra.api import FactBase


class PipPackages(FactBase):
    '''
    Returns a dict of installed pip packages:

    .. code:: python

        'package_name': 'version',
        ...
    '''

    command = 'pip freeze'
    _regex = r'^([a-zA-Z0-9_\-\+\.]+)==([0-9\.]+[a-z0-9\-]*)$'

    def process(self, output):
        packages = {}

        for line in output:
            matches = re.match(self._regex, line)
            if matches:
                # pip packages are case-insensitive
                name = matches.group(1).lower()
                packages[name] = matches.group(2)

        return packages


class PipPackagesVirtualenv(PipPackages):
    def command(self, venv):
        # Remove any trailing slash
        venv = venv.rstrip('/')
        return '{0}/bin/pip freeze'.format(venv)
