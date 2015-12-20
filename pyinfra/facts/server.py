# pyinfra
# File: pyinfra/facts/server.py
# Desc: server/os related facts

import re

from dateutil.parser import parse as parse_date

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
        return parse_date(output[0])


class Users(FactBase):
    '''
    Gets & returns a dict of users -> details:

    .. code:: python

        'user_name': {
            'uid': 1,
            'gid': 1,
            'home': '/home/user_name',
            'shell': '/bin/bash
        },
        ...
    '''

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
    '''
    Returns a dict of the Linux distribution version. Ubuntu, CentOS & Debian currently:

    .. code:: python

        {
            'name': 'CentOS',
            'major': 6,
            'minor': 5
        }
    '''

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
