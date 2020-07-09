from __future__ import unicode_literals

import re
from datetime import datetime

from dateutil.parser import parse as parse_date

from pyinfra.api import FactBase, ShortFactBase
from pyinfra.api.util import try_int


class Home(FactBase):
    '''
    Returns the home directory of the current user.
    '''

    command = 'echo $HOME'


class Hostname(FactBase):
    '''
    Returns the current hostname of the server.
    '''

    command = 'hostname'


class Os(FactBase):
    '''
    Returns the OS name according to ``uname``.
    '''

    command = 'uname -s'


class OsVersion(FactBase):
    '''
    Returns the OS version according to ``uname``.
    '''

    command = 'uname -r'


class Arch(FactBase):
    '''
    Returns the system architecture according to ``uname``.
    '''

    command = 'uname -p'


class Command(FactBase):
    '''
    Returns the raw output lines of a given command.
    '''

    @staticmethod
    def command(command):
        return command


class Which(FactBase):
    '''
    Returns the path of a given command, if available.
    '''

    use_default_on_error = True

    @staticmethod
    def command(name):
        return 'which {0}'.format(name)


class Date(FactBase):
    '''
    Returns the current datetime on the server.
    '''

    command = 'LANG=C date'
    default = datetime.now

    @staticmethod
    def process(output):
        return parse_date(output[0])


class Mounts(FactBase):
    '''
    Returns a dictionary of mounted filesystems and information.

    .. code:: python

        "/": {
            "device": "/dev/mv2",
            "type": "ext4",
            "options": [
                "rw",
                "relatime"
            ]
        },
        ...
    '''

    command = 'mount'
    default = dict

    @staticmethod
    def process(output):
        devices = {}

        for line in output:
            is_map = False
            if line.startswith('map '):
                line = line[4:]
                is_map = True

            device, _, path, other_bits = line.split(' ', 3)

            if is_map:
                device = 'map {0}'.format(device)

            if other_bits.startswith('type'):
                _, type_, options = other_bits.split(' ', 2)
                options = options.strip('()').split(',')
            else:
                options = other_bits.strip('()').split(',')
                type_ = options.pop(0)

            devices[path] = {
                'device': device,
                'type': type_,
                'options': [option.strip() for option in options],
            }

        return devices


class KernelModules(FactBase):
    '''
    Returns a dictionary of kernel module name -> info.

    .. code:: python

        'module_name': {
            'size': 0,
            'instances': 0,
            'state': 'Live',
        },
        ...
    '''

    command = 'cat /proc/modules'
    default = dict

    @staticmethod
    def process(output):
        modules = {}

        for line in output:
            name, size, instances, depends, state, _ = line.split(' ', 5)
            instances = int(instances)

            module = {
                'size': size,
                'instances': instances,
                'state': state,
            }

            if depends != '-':
                module['depends'] = [
                    value
                    for value in depends.split(',')
                    if value
                ]

            modules[name] = module

        return modules


class LsbRelease(FactBase):
    '''
    Returns a dictionary of release information using ``lsb_release``.

    .. code:: python

        {
            "id": "Ubuntu",
            "description": "Ubuntu 18.04.2 LTS",
            "release": "18.04",
            "codename": "bionic",
            ...
        }
    '''

    command = 'lsb_release -ca'

    @staticmethod
    def process(output):
        items = {}

        for line in output:
            if ':' not in line:
                continue

            key, value = line.split(':', 1)

            key = key.strip().lower()

            # Turn "distributor id" into "id"
            if ' ' in key:
                key = key.split(' ')[-1]

            value = value.strip()

            items[key] = value

        return items


class Sysctl(FactBase):
    '''
    Returns a dictionary of sysctl settings and values.

    .. code:: python

        {
            "fs.inotify.max_queued_events": 16384,
            "fs.inode-state": [
                44565,
                360,
            ],
            ...
        }
    '''

    command = 'sysctl -a'
    default = dict

    @staticmethod
    def process(output):
        sysctls = {}

        for line in output:
            key = values = None

            if '=' in line:
                key, values = line.split('=', 1)
            elif ':' in line:
                key, values = line.split(':', 1)
            else:
                continue  # pragma: no cover

            if key and values:
                key = key.strip()
                values = values.strip()

                if re.match(r'^[a-zA-Z0-9_\.\s]+$', values):
                    values = [
                        try_int(item.strip())
                        for item in values.split()
                    ]

                    if len(values) == 1:
                        values = values[0]

                sysctls[key] = values

        return sysctls


class Groups(FactBase):
    '''
    Returns a list of groups on the system.
    '''

    command = 'cat /etc/group'
    default = list

    @staticmethod
    def process(output):
        groups = []

        for line in output:
            if ':' in line:
                groups.append(line.split(':')[0])

        return groups


class Crontab(FactBase):
    '''
    Returns a dictionary of cron command -> execution time.

    .. code:: python

        '/path/to/command': {
            'minute': '*',
            'hour': '*',
            'month': '*',
            'day_of_month': '*',
            'day_of_week': '*',
        },
        ...
    '''

    default = dict

    @staticmethod
    def command(user=None):
        if user:
            return 'crontab -l -u {0}'.format(user)

        return 'crontab -l'

    @staticmethod
    def process(output):
        crons = {}
        current_comments = []

        for line in output:
            line = line.strip()
            if not line or line.startswith('#'):
                current_comments.append(line)
                continue

            minute, hour, day_of_month, month, day_of_week, command = line.split(' ', 5)
            crons[command] = {
                'minute': try_int(minute),
                'hour': try_int(hour),
                'month': try_int(month),
                'day_of_month': try_int(day_of_month),
                'day_of_week': try_int(day_of_week),
                'comments': current_comments,
            }
            current_comments = []

        return crons


class Users(FactBase):
    '''
    Returns a dictionary of users -> details.

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
            ID=`id $i`;
            META=`cat /etc/passwd | grep ^$i: | cut -d: -f6-7`;
            echo "$ID $META";
        done
    '''.strip()

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
                        continue  # pragma: no cover

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
        r'(Alpine) Linux v([0-9]+).([0-9]+)',
    ]

    name_to_pretty_name = {
        'Centos': 'CentOS',
        'Opensuse-Tumbleweed': 'openSUSE',
        'Opensuse-Leap': 'openSUSE',
    }

    use_default_on_error = True

    @staticmethod
    def default():
        return {
            'name': None,
            'major': None,
            'minor': None,
        }

    def process(self, output):
        meta = {}

        for line in output:
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=')
                meta[key] = value.strip('"')

        name = None
        major = None
        minor = None

        if 'ID' in meta and 'VERSION_ID' in meta:
            name = meta['ID'].title()
            version_bits = meta['VERSION_ID'].split('.')
            major = version_bits[0]
            if len(version_bits) > 1:
                minor = version_bits[1]
        else:
            for line in output:
                matched = False
                for regex in self.regexes:
                    matches = re.search(regex, line)
                    if matches:
                        name = matches.group(1)
                        major = matches.group(2)
                        minor = matches.group(3)
                        matched = True
                        break
                if matched:
                    break

        release_info = self.default()
        release_info.update({
            'name': self.name_to_pretty_name.get(name, name),
            'major': try_int(major),
            'minor': try_int(minor),
            'release_meta': meta,
        })

        return release_info


class LinuxName(ShortFactBase):
    '''
    Returns the name of the Linux distribution. Shortcut for
    ``host.fact.linux_distribution['name']``.
    '''

    fact = LinuxDistribution

    @staticmethod
    def process_data(data):
        return data['name']
