# pyinfra
# File: pyinfra/facts/pip.py
# Desc: facts for the pip package manager

from __future__ import unicode_literals

from pyinfra import logger
from pyinfra.api import FactBase

from .util.packaging import parse_packages


class PipPackages(FactBase):
    '''
    Returns a dict of installed pip packages globally or in a given virtualenv:

    .. code:: python

        'package_name': 'version',
        ...
    '''

    default = {}
    command = 'pip freeze'
    _regex = r'^([a-zA-Z0-9_\-\+\.]+)==([0-9\.]+[a-z0-9\-]*)$'

    def command(self, venv=None):
        if venv:
            venv = venv.rstrip('/')
            return '{0}/bin/pip freeze'.format(venv)

        else:
            return 'pip freeze'

    def process(self, output):
        return parse_packages(self._regex, output)


# TODO: remove at some point
# COMPAT: above now covers both use cases
class PipVirtualenvPackages(PipPackages):
    '''
    [DEPRECATED] Maintained for backwards-compatability.
    '''

    def command(self, *args, **kwargs):
        logger.warning('The pip_virtualenv_packages fact is depreciated, please use pip_packages')
        return super(PipVirtualenvPackages, self).command(*args, **kwargs)
