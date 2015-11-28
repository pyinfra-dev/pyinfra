# pyinfra
# File: pyinfra/facts/yum.py
# Desc: facts for the yum package manager and rpm files

import re

from pyinfra.api import FactBase


class YumSources():
    '''
    Returns a dict of installed yum sources.
    '''
    pass


class RPMPackages(FactBase):
    '''
    Returns a dict of installed rpm packages:

    .. code:: python

        'package_name': 'version',
        ...
    '''
    command = 'rpm -qa'
    _regex = r'^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.\-]+)\.[a-z0-9_]+\.[a-z0-9_\.]+$'

    def process(self, output):
        packages = {}
        for line in output:
            matches = re.match(self._regex, line)
            if matches:
                packages[matches.group(1)] = matches.group(2)

        return packages


class RPMPackage():
    '''
    Returns information on a .rpm file.
    '''
    pass
