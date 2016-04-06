# pyinfra
# File: pyinfra/facts/gem.py
# Desc: facts for the RubyGems package manager

from pyinfra.api import FactBase

from .util.packaging import parse_packages


class GemPackages(FactBase):
    '''
    Returns a dict of installed gem packages:

    .. code:: python

        'package_name': 'version',
        ...
    '''

    default = {}
    command = 'gem list --local'
    _regex = r'^([a-zA-Z0-9\-\+\_]+)\s\(([0-9\.]+)\)$'

    def process(self, output):
        return parse_packages(self._regex, output)
