# pyinfra
# File: pyinfra/facts/yum.py
# Desc: facts for the yum package manager and rpm files

import re

from pyinfra.api import FactBase

RPM_PACKAGE_RE = r'^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.\-]+)\.[a-z0-9_]+\.[a-z0-9_\.]+$'


class RPMPackages(FactBase):
    '''
    Returns a dict of installed rpm packages:

    .. code:: python

        'package_name': 'version',
        ...
    '''
    command = 'rpm -qa'

    def process(self, output):
        packages = {}
        for line in output:
            matches = re.match(RPM_PACKAGE_RE, line)
            if matches:
                packages[matches.group(1)] = matches.group(2)

        return packages


class RpmPackage(FactBase):
    '''
    Returns information on a .rpm file.
    '''

    def command(self, name):
        return 'rpm -qp {0}'.format(name)

    def process(self, output):
        for line in output:
            matches = re.match(RPM_PACKAGE_RE, line)
            if matches:
                return {
                    'name': matches.group(1),
                    'version': matches.group(2)
                }
