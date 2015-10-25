# pyinfra
# File: pyinfra/facts/packages.py
# Desc: various package management system facts

import re

from pyinfra.api import FactBase


class DebPackages(FactBase):
    '''Returns a dict of installed dpkg packages -> version.'''
    command = 'dpkg -l'
    regex = r'^[a-z]+\s+([a-zA-Z0-9\+\-\.]+):?[a-zA-Z0-9]*\s+([a-zA-Z0-9:~\.\-\+]+).+$'

    def process(self, output):
        packages = {}
        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                # apt packages are case-insensitive
                name = matches.group(1).lower()
                packages[name] = matches.group(2)

        return packages


class RPMPackages(FactBase):
    '''Returns a dict of installed rpm packages -> version.'''
    command = 'rpm -qa'
    regex = r'^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.\-]+)\.[a-z0-9_]+\.[a-z0-9_\.]+$'

    def process(self, output):
        packages = {}
        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                packages[matches.group(1)] = matches.group(2)

        return packages


class PkgPackages(FactBase):
    '''Returns a dict of installed pkg packages -> version.'''
    command = 'pkg_info'
    regex = r'^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.]+)'

    def process(self, output):
        packages = {}
        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                packages[matches.group(1)] = matches.group(2)

        return packages


class PipPackages(FactBase):
    '''Returns a dict of installed pip packages -> version.'''
    command = 'pip freeze'
    regex = r'^([a-zA-Z0-9_\-\+]+)==([0-9\.]+)$'

    def process(self, output):
        packages = {}
        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                # pip packages are case-insensitive
                name = matches.group(1).lower()
                packages[name] = matches.group(2)

        return packages

class PipPackagesVenv(PipPackages):
    def command(self, venv):
        # Remove any trailing slash
        venv = venv.rstrip('/')
        return '{0}/bin/pip freeze'.format(venv)
