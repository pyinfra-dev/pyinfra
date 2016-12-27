# pyinfra
# File: pyinfra/facts/pip.py
# Desc: facts for the pip package manager

from __future__ import unicode_literals

from pyinfra import logger
from pyinfra.api import FactBase

from .util.packaging import parse_packages


class PipPackages(FactBase):
    '''
    Returns a dict of installed pip packages:

    .. code:: python

        'package_name': 'version',
        ...
    '''

    default = {}
    _regex = r'^([a-zA-Z0-9_\-\+\.]+)==([0-9\.]+[a-z0-9\-]*)$'

    def command(self, pip='pip'):
        return '{0} freeze'.format(pip)

    def process(self, output):
        return parse_packages(self._regex, output)


# TODO: remove at some point
# COMPAT: above now covers both use cases
class PipVirtualenvPackages(PipPackages):
    '''
    [DEPRECATED] Maintained for backwards-compatability.
    '''

    def command(self, *args, **kwargs):
        logger.warning('The pip_virtualenv_packages fact is depreciated and will be removed in 0.3, please use pip_packages')
        return super(PipVirtualenvPackages, self).command(*args, **kwargs)
