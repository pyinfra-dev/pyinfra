# pyinfra
# File: pyinfra/facts/apt.py
# Desc: facts for the apt package manager & deb files

from __future__ import unicode_literals

import re

import six

from pyinfra.api import FactBase

from .util.packaging import parse_packages


def parse_apt_repo(name):
    regex = r'^(deb(?:-src)?)(?:\s+\[([a-zA-Z0-9=\s]+)\])?\s+([^\s]+)\s+([a-z-]+)\s+([a-z-\s]*)$'

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

    command = 'cat /etc/apt/sources.list /etc/apt/sources.list.d/*.list'
    default = list

    def process(self, output):
        repos = []

        for line in output:
            repo = parse_apt_repo(line)
            if repo:
                repos.append(repo)

        return repos


class DebPackages(FactBase):
    '''
    Returns a dict of installed dpkg packages:

    .. code:: python

        'package_name': 'version',
        ...
    '''

    command = 'dpkg -l'
    regex = r'^[a-z]+\s+([a-zA-Z0-9\+\-\.]+):?[a-zA-Z0-9]*\s+([a-zA-Z0-9:~\.\-\+]+).+$'
    default = dict

    def process(self, output):
        return parse_packages(self.regex, output)


class DebPackage(FactBase):
    '''
    Returns information on a .deb file.
    '''

    _regexes = {
        'name': r'^Package: ([a-zA-Z0-9\-]+)$',
        'version': r'^Version: ([0-9\.\-]+)$',
    }

    def command(self, name):
        return 'dpkg -I {0}'.format(name)

    def process(self, output):
        data = {}

        for line in output:
            for key, regex in six.iteritems(self._regexes):
                matches = re.match(regex, line)
                if matches:
                    value = matches.group(1)
                    data[key] = value
                    break

        return data
