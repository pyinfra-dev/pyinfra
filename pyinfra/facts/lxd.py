import json

from pyinfra.api import FactBase


class LXDContainers(FactBase):
    '''
    Returns a list of running LXD containers
    '''

    command = 'which lxc > /dev/null && lxc list --format json --fast || true'
    default = list

    def process(self, output):
        assert len(output) == 1
        return json.loads(output[0])
