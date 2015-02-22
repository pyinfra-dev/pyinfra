# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

import re
from inspect import isclass
from inflection import underscore


class Distribution:
    '''Returns the Linux distribution. Ubuntu, CentOS & Debian currently'''
    command = 'cat /etc/*-release'
    # Currently supported distros
    regexes = [
        r'(Ubuntu) ([0-9]{2})\.([0-9]{2})',
        r'(CentOS) release ([0-9]).([0-9])',
        r'(Debian) GNU/Linux ([0-9])()'
    ]

    def process(self, output):
        output = '\n'.join(output)

        for regex in self.regexes:
            matches = re.search(regex, output)
            if matches:
                return {
                    'name': matches.group(1),
                    'major': matches.group(2),
                    'minor': matches.group(3)
                }

        return {'name': 'Unknown'}


class Users:
    '''Gets & returns a dict of users -> details'''
    command = 'cat /etc/passwd'

    def process(self, output):
        users = {}
        for line in output:
            name, _, uid, gid, _, home, shell = line.split(':')
            users[name] = {
                'uid': uid,
                'gid': gid,
                'home': home,
                'shell': shell
            }

        return users


class NetworkDevices:
    '''Gets & returns a dict of network devices -> details'''
    command = 'cat /proc/net/dev'
    regex = r'\s+([a-zA-Z0-9]+):\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)'

    def process(self, output):
        devices = {}
        for line in output:
            matches = re.match(self.regex, line)
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


class BlockDevices:
    '''Returns a dict of (mounted, atm) block devices -> details'''
    command = 'df -T'
    regex = r'([a-zA-Z0-9\/\-_]+)\s+([a-zA-Z0-9\/-_]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]{1,3})%\s+([a-zA-Z\/0-9\-_]+)'

    def process(self, output):
        devices = {}
        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                if matches.group(1) == 'none': continue
                devices[matches.group(1)] = {
                    'type': matches.group(2),
                    'blocks': matches.group(3),
                    'used': matches.group(4),
                    'available': matches.group(5),
                    'used_percent': matches.group(6),
                    'mount': matches.group(7)
                }

        return devices


class DebPackages:
    '''Returns a dict of installed dpkg packages -> details'''
    command = 'dpkg -l'
    regex = r'[a-z]+\s+([a-zA-Z0-9:\+\-\.]+)\s+([a-zA-Z0-9:~\.\-\+]+)\s+([a-z0-9]+)'

    def process(self, output):
        packages = {}
        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                packages[matches.group(1)] = {
                    'version': matches.group(2)
                }

        return packages


class RPMPackages:
    '''Returns a dict of installed rpm packages -> details'''
    command = 'rpm -qa'
    regex = r'([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.\-]+)\.([a-z0-9_]+)\.([a-z0-9_\.]+)'

    def process(self, output):
        packages = {}
        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                packages[matches.group(1)] = {
                    'version': matches.group(2),
                    'arch': matches.group(4)
                }

        return packages


# Build dynamic facts & fact lists dicts
FACTS = {
    underscore(name): class_def()
    for name, class_def in locals().iteritems()
    if isclass(class_def) and class_def.__module__ == __name__
}
