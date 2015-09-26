# pyinfra
# File: pyinfra/facts/server.py
# Desc: server/os related facts

import re
from datetime import datetime

from pyinfra.api import FactBase


class Home(FactBase):
    command = 'echo $HOME'


class Hostname(FactBase):
    command = 'hostname'


class Os(FactBase):
    command = 'uname -s'


class OsVersion(FactBase):
    command = 'uname -r'


class Arch(FactBase):
    command = 'uname -p'


class Date(FactBase):
    '''Returns the current datetime on the server.'''
    command = 'date'

    def process(self, output):
        # Remove the timezone as local Python might not be aware (Python fail right there)
        bits = output[0].split(' ')
        datestring_no_tz = u' '.join(bits[0:4] + [bits[5]])
        return datetime.strptime(datestring_no_tz, '%a %b %d %H:%M:%S %Y')


class Users(FactBase):
    '''Gets & returns a dict of users -> details.'''
    command = 'cat /etc/passwd'

    def process(self, output):
        users = {}
        for line in output:
            try:
                name, _, uid, gid, _, home, shell = line.split(':')
            # Invalid /etc/passwd line?
            except ValueError:
                continue

            users[name] = {
                'uid': uid,
                'gid': gid,
                'home': home,
                'shell': shell
            }

        return users


class LinuxDistribution(FactBase):
    '''Returns the Linux distribution. Ubuntu, CentOS & Debian currently.'''
    command = 'cat /etc/*-release'
    # Currently supported distros
    regexes = [
        r'(Ubuntu) ([0-9]{2})\.([0-9]{2})',
        r'(CentOS) release ([0-9]).([0-9])',
        r'(CentOS) Linux release ([0-9]).([0-9])',
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
