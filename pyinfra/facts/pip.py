from __future__ import unicode_literals

from pyinfra.api import FactBase

from .util.packaging import parse_packages

PIP_REGEX = r'^([a-zA-Z0-9_\-\+\.]+)==([0-9\.]+[a-z0-9\-]*)$'


class PipPackages(FactBase):
    '''
    Returns a dict of installed pip packages:

    .. code:: python

        'package_name': ['version'],
        ...
    '''

    default = dict

    def command(self, pip='pip'):
        return '{0} freeze --all'.format(pip)

    def process(self, output):
        return parse_packages(PIP_REGEX, output)
