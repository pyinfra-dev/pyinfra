from __future__ import unicode_literals

from pyinfra.api import FactBase

import json


class PipxPackages(FactBase):
    '''
    Returns a dict of installed pipx packages:

    .. code:: python

        {
            'package_name': ['version'],
        }
    '''

    default = dict
    pipx_command = 'pipx'

    def requires_command(self, pipx=None):
        return pipx or self.pipx_command

    def command(self, pipx=None):
        pipx = pipx or self.pipx_command
        return '{0} list --json'.format(pipx)

    def process(self, output):
        pipx_list= json.loads(output)
        versions={}
        for venv in pipx_list['venvs'].values():
            package=venv['metadata']['main_package']['package']
            version=venv['metadata']['main_package']['package_version']
            versions[package]={version}
        return versions
