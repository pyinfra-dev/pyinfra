from __future__ import unicode_literals

import re

from pyinfra.api import FactBase


def parse_apt_repo(name):
    regex = r'^(deb(?:-src)?)(?:\s+\[([a-zA-Z0-9=,\s]+)\])?\s+([^\s]+)\s+([a-z-]+)\s+([a-z-\s]*)$'

    matches = re.match(regex, name)

    if not matches:
        return

    # Parse any options
    options = {}
    options_string = matches.group(2)
    if options_string:
        for option in options_string.split():
            key, value = option.split('=', 1)
            if ',' in value:
                value = value.split(',')

            options[key] = value

    return {
        'options': options,
        'type': matches.group(1),
        'url': matches.group(3),
        'distribution': matches.group(4),
        'components': set(matches.group(5).split()),
    }


class AptSources(FactBase):
    '''
    Returns a list of installed apt sources:

    .. code:: python

        {
            'type': 'deb',
            'url': 'http://archive.ubuntu.org',
            'distribution': 'trusty',
            'components', ['main', 'multiverse']
        },
        ...
    '''

    command = 'cat /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2> /dev/null || true'
    default = list

    def process(self, output):
        repos = []

        for line in output:
            repo = parse_apt_repo(line)
            if repo:
                repos.append(repo)

        return repos
