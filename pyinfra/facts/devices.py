# pyinfra
# File: pyinfra/facts/devices.py
# Desc: device (nics, hdds, etc) facts

import re

from pyinfra.api import FactBase


class BlockDevices(FactBase):
    '''Returns a dict of (mounted) block devices -> details.'''
    command = 'df'
    _regex = r'([a-zA-Z0-9\/\-_]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]{1,3})%\s+([a-zA-Z\/0-9\-_]+)'

    def process(self, output):
        devices = {}
        for line in output:
            matches = re.match(self._regex, line)
            if matches:
                if matches.group(1) == 'none': continue
                devices[matches.group(1)] = {
                    'blocks': matches.group(2),
                    'used': matches.group(3),
                    'available': matches.group(4),
                    'used_percent': matches.group(5),
                    'mount': matches.group(6)
                }

        return devices


class NetworkDevices():
    '''[Broken (no baseclass)] Gets & returns a dict of network devices -> details.'''
    command = 'ifconfig'
    _regex = r'\s+([a-zA-Z0-9]+):\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)'

    def process(self, output):
        devices = {}
        for line in output:
            matches = re.match(self._regex, line)
            if matches:
                devices[matches.group(1)] = {
                    'receive': {
                        'bytes': matches.group(2),
                        'packets': matches.group(3),
                        'errors': matches.group(4),
                        'drop': matches.group(5),
                        'fifo': matches.group(6),
                        'frame': matches.group(7),
                        'compressed': matches.group(8),
                        'multicast': matches.group(9)
                    },
                    'transmit': {
                        'bytes': matches.group(10),
                        'packets': matches.group(11),
                        'errors': matches.group(12),
                        'drop': matches.group(13),
                        'fifo': matches.group(14),
                        'colls': matches.group(15),
                        'carrier': matches.group(16),
                        'compressed': matches.group(17)
                    }
                }

        return devices
