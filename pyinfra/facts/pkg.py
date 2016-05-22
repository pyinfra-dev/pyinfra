# pyinfra
# File: pyinfra/facts/pkg.py
# Desc: facts for the BSD pkg_* package manager

from pyinfra.api import FactBase

from .util.packaging import parse_packages


class PkgPackages(FactBase):
    '''
    Returns a dict of installed pkg packages:

    .. code:: python

        'package_name': 'version',
        ...
    '''

    default = {}
    command = 'pkg_info'
    _regex = r'^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.]+)'

    def process(self, output):
        return parse_packages(self._regex, output)
