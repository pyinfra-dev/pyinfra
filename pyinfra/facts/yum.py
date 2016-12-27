# pyinfra
# File: pyinfra/facts/yum.py
# Desc: facts for the yum package manager and rpm files

from __future__ import unicode_literals

import re

from pyinfra.api import FactBase

from .util.packaging import parse_packages

rpm_regex = r'^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.\-]+)\.[a-z0-9_\.]+$'


class RPMPackages(FactBase):
    '''
    Returns a dict of installed rpm packages:

    .. code:: python

        'package_name': 'version',
        ...
    '''

    default = {}
    command = 'rpm -qa'

    def process(self, output):
        return parse_packages(
            rpm_regex, output,
            # yum packages are case-sensitive
            lower=False,
        )


class RpmPackage(FactBase):
    '''
    Returns information on a .rpm file:

    .. code:: python

        {
            'name': 'my_package',
            'version': '1.0.0'
        }
    '''

    def command(self, name):
        return 'rpm -qp {0}'.format(name)

    def process(self, output):
        for line in output:
            matches = re.match(rpm_regex, line)
            if matches:
                return {
                    'name': matches.group(1),
                    'version': matches.group(2),
                }
