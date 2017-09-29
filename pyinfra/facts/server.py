# pyinfra
# File: pyinfra/facts/server.py
# Desc: server/os related facts

from __future__ import unicode_literals

import re
from datetime import datetime

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


class Command(FactBase):
    def command(self, command):
        return command


class Which(FactBase):
    def command(self, name):
        return 'which {0}'.format(name)


class Date(FactBase):
    '''Returns the current datetime on the server.'''

    command = 'LANG=C date'
    default = datetime.now

    def process(self, output):
        return parse_date(output[0])


class LsbRelease(FactBase):
    command = 'lsb_release -ca'

    def process(self, output):
        items = {}

        for line in output:
            if ':' not in line:
                continue

            key, value = line.split(':')

            key = key.strip().lower()

            # Turn "distributor id" into "id"
            if ' ' in key:
                key = key.split(' ')[-1]

            value = value.strip()

            items[key] = value

        return items


class Groups(FactBase):
    '''
    Returns a list of groups on the system.
    '''

    command = 'cat /etc/group'
    default = list

    def process(self, output):
        groups = []

        for line in output:
            if ':' in line:
                groups.append(line.split(':')[0])

        return groups


class Users(FactBase):
    '''
    Returns a dict of users -> details:

    .. code:: python

        'user_name': {
            'home': '/home/user_name',
            'shell': '/bin/bash,
            'group': 'main_user_group',
            'groups': [
                'other',
                'groups'
            ]
        },
        ...
    '''

    command = '''
        for i in `cat /etc/passwd | cut -d: -f1`; do
            ID=`id $i`
            META=`cat /etc/passwd | grep ^$i: | cut -d: -f6-7`
            echo "$ID $META"
        done
    '''

    default = dict

    regex = r'^uid=[0-9]+\(([a-zA-Z0-9_\.\-]+)\) gid=[0-9]+\(([a-zA-Z0-9_\.\-]+)\) groups=([a-zA-Z0-9_\.\-,\(\)\s]+) (.*)$'  # noqa
    group_regex = r'^[0-9]+\(([a-zA-Z0-9_\.\-]+)\)$'

    def process(self, output):
        users = {}
        for line in output:
            matches = re.match(self.regex, line)

            if matches:
                # Parse out the home/shell
                home_shell = matches.group(4)
                home = shell = None

                # /blah: is just a home
                if home_shell.endswith(':'):
                    home = home_shell[:-1]

                # :/blah is just a shell
                elif home_shell.startswith(':'):
                    shell = home_shell[1:]

                # Both home & shell
                elif ':' in home_shell:
                    home, shell = home_shell.split(':')

                # Main user group
                group = matches.group(2)

                # Parse the groups
                groups = []
                for group_matches in matches.group(3).split(','):
                    name = re.match(self.group_regex, group_matches.strip())
                    if name:
                        name = name.group(1)
                    else:
                        continue

                    # We only want secondary groups here
                    if name != group:
                        groups.append(name)

                users[matches.group(1)] = {
                    'group': group,
                    'groups': groups,
                    'home': home,
                    'shell': shell,
                }

        return users


class LinuxDistribution(FactBase):
    '''
    Returns a dict of the Linux distribution version. Ubuntu, Debian, CentOS,
    Fedora & Gentoo currently. Also contains any key/value items located in
    release files.

    .. code:: python

        {
            'name': 'CentOS',
            'major': 6,
            'minor': 5,
            'release_meta': {
                'DISTRIB_CODENAME': 'trusty',
                ...
            }
        }
    '''

    command = 'cat /etc/*-release'

    # Currently supported distros
    regexes = [
        r'(Ubuntu) ([0-9]{2})\.([0-9]{2})',
        r'(CentOS) release ([0-9]).([0-9])',
        r'(Red Hat Enterprise Linux) Server release ([0-9]).([0-9])',
        r'(CentOS) Linux release ([0-9])\.([0-9])',
        r'(Debian) GNU/Linux ([0-9])()',
        r'(Gentoo) Base System release ([0-9])\.([0-9])',
        r'(Fedora) release ([0-9]+)()',
    ]

    @staticmethod
    def default():
        return {
            'name': None,
            'major': None,
            'minor': None,
        }

    def process(self, output):
        release_info = {
            'release_meta': {},
        }

        # Start with a copy of the default (None) data
        release_info.update(self.default())

        for line in output:
            # Check if we match a known version/major/minor string
            for regex in self.regexes:
                matches = re.search(regex, line)
                if matches:
                    release_info.update({
                        'name': matches.group(1),
                        'major': matches.group(2) and int(matches.group(2)) or None,
                        'minor': matches.group(3) and int(matches.group(3)) or None,
                    })

            if '=' in line:
                key, value = line.split('=')
                release_info['release_meta'][key] = value.strip('"')

        return release_info
