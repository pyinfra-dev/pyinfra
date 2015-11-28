# pyinfra
# File: pyinfra/facts/pkg.py
# Desc: facts for the BSD pkg_* package manager

import re

from pyinfra.api import FactBase


class PkgPackages(FactBase):
    '''
    Returns a dict of installed pkg packages:

    .. code:: python

        'package_name': 'version',
        ...
    '''
    command = 'pkg_info'
    _regex = r'^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.]+)'

    def process(self, output):
        packages = {}
        for line in output:
            matches = re.match(self._regex, line)
            if matches:
                packages[matches.group(1)] = matches.group(2)

        return packages
