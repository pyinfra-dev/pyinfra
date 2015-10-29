# pyinfra
# File: pyinfra/facts/apt.py
# Desc: facts for the apt package manager

import re

from pyinfra.api import FactBase


def parse_apt_repo(name):
    regex = r'^(deb(?:-src)?)\s+([^\s]+)\s+([a-z-]+)\s+([a-z-\s]*)$'

    matches = re.match(regex, name)
    if matches:
        return matches.group(2), {
            'type': matches.group(1),
            'distribution': matches.group(3),
            'components': matches.group(4).split()
        }


class AptSources(FactBase):
    '''
    Returns a dict of installed apt sources:

    .. code:: python

        "http://archive.ubuntu.org": {
            'type': 'deb',
            'distribution': 'trusty',
            'components', ['main', 'multiverse']
        },
        ...
    '''

    command = 'cat /etc/apt/sources.list /etc/apt/sources.list.d/*.list | grep -v "#"'

    def process(self, output):
        repos = {}
        for line in output:
            repo = parse_apt_repo(line)
            if repo:
                url, data = repo
                repos[url] = data

        return repos
