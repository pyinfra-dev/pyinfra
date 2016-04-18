# pyinfra
# File: pyinfra/facts/apt.py
# Desc: facts for the apt package manager & deb files

from __future__ import unicode_literals

import re

import six

from pyinfra.api import FactBase

from .util.packaging import parse_packages


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

        'http://archive.ubuntu.org': {
            'type': 'deb',
            'distribution': 'trusty',
            'components', ['main', 'multiverse']
        },
        ...
    '''

    default = {}
    command = 'cat /etc/apt/sources.list /etc/apt/sources.list.d/*.list | grep -v "#"'

    def process(self, output):
        repos = {}
        for line in output:
            repo = parse_apt_repo(line)
            if repo:
                url, data = repo
                repos[url] = data

        return repos


class DebPackages(FactBase):
    '''
    Returns a dict of installed dpkg packages:

    .. code:: python

        'package_name': 'version',
        ...
    '''

    default = {}
    command = 'dpkg -l'
    _regex = r'^[a-z]+\s+([a-zA-Z0-9\+\-\.]+):?[a-zA-Z0-9]*\s+([a-zA-Z0-9:~\.\-\+]+).+$'

    def process(self, output):
        return parse_packages(self._regex, output)


class DebPackage(FactBase):
    '''
    Returns information on a .deb file.
    '''

    _regexes = {
        'name': r'^Package: ([a-zA-Z0-9\-]+)$',
        'version': r'^Version: ([0-9\.\-]+)$'
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
