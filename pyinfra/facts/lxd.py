# pyinfra
# File: pyinfra/facts/lxd.py
# Desc: LXD containers facts

import json

from pyinfra.api import FactBase


class LXDContainers(FactBase):
    '''
    Returns a list of running LXD containers
    '''

    command = 'lxc list --format json --fast'

    def process(self, output):
        assert len(output) == 1
        return json.loads(output[0])
