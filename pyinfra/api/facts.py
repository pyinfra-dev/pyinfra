# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

import re
from inspect import isclass


# Returns the list of users
class fact_Users:
    command = 'cat /etc/passwd'

    def process(self, output):
        users = {}
        for line in output.splitlines():
            name, _, uid, gid, _, home, shell = line.split(':')
            users[name] = {
                'uid': uid,
                'gid': gid,
                'home': home,
                'shell': shell
            }

        return users


# Returns the Linux distribution
# Ubuntu, CentOS & Debian currently
class fact_Distribution:
    command = 'cat /etc/*-release'
    # Currently supported distros
    regexes = [
        r'(Ubuntu) ([0-9]{2})\.([0-9]{2})',
        r'(CentOS) release ([0-9]).([0-9])',
        r'(Debian) GNU/Linux ([0-9])()'
    ]

    def process(self, output):
        for regex in self.regexes:
            matches = re.search(regex, output)
            if matches:
                return {
                    'name': matches.group(1),
                    'major': matches.group(2),
                    'minor': matches.group(3)
                }


# class fact_NetworkDevices


# class fact_BlockDevices


# Build dynamic facts & fact lists dicts
FACTS = {
    name[5:]: class_def()
    for name, class_def in locals().iteritems()
    if name.startswith('fact_') and isclass(class_def)
}
