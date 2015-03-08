# pyinfra
# File: api/host.py
# Desc: a classmodule representing a single host/server

'''
This file provides a class representing the current Linux server & it's state. When accessing
methods or properties, remote checks are run on all remote hosts simultaneously & cached.
'''

import re

from termcolor import colored

import pyinfra
from pyinfra import logger

from .facts import FACTS
from .ssh import run_all_command


symbol_to_octal_permissions = {
    'rwx': '7',
    'rw-': '6',
    'r-x': '5',
    'r--': '4',
    '-wx': '3',
    '-w-': '2',
    '--x': '1'
}
ls_regex = re.compile(
    '[a-z-]?([-rwx]{9})\.?\s+[0-9]+\s+([a-zA-Z]+)\s+([a-zA-Z]+)\s+([0-9]+)\s+[a-zA-Z]{3}\s+[0-9]+\s+[0-9]{2}:[0-9]{2}'
)
def _ls_matches_to_dict(matches):
    '''Parse permissions into octal format (which is what we compare to deploy scripts).'''
    def parse_permissions(permissions):
        result = ''
        # owner, group, world
        for group in [permissions[0:3], permissions[3:6], permissions[6:9]]:
            if group in symbol_to_octal_permissions:
                result = '{}{}'.format(result, symbol_to_octal_permissions[group])
            else:
                result = '{}0'.format(result)

        return result

    return {
        'permissions': parse_permissions(matches.group(1)),
        'user': matches.group(2),
        'group': matches.group(3),
        'size': matches.group(4)
    }


def _assign_facts(outs, key, processor, accessor=None):
    '''Process & assign facts to all servers.'''
    for (server, stdout, stderr) in outs:
        result = processor(stdout)

        if accessor is None:
            pyinfra._facts[server][key] = result
        else:
            pyinfra._facts[server][accessor][key] = result

        logger.debug('Fact {0} for {1} assigned to {2}'.format(key, server, result))


class Host(object):
    def __getattr__(self, key):
        if key not in FACTS:
            raise AttributeError('No such fact: {}'.format(key))

        current_server_facts = pyinfra._facts[pyinfra._current_server]

        # Already got this fact?
        if key in current_server_facts:
            return current_server_facts[key]

        logger.info('Running fact {}'.format(colored(key, attrs=['bold'])))
        # For each server, spawn a job on the pool to gather the fact
        outs = run_all_command(FACTS[key].command)

        # Process & assign each fact to pyinfra._facts
        _assign_facts(outs, key, FACTS[key].process)

        # Return the fact
        return pyinfra._facts[pyinfra._current_server][key]

    def directory(self, name):
        '''Like a fact, but for directory information.'''
        current_server_dirs = pyinfra._facts[pyinfra._current_server]['_dirs']

        # Already got this directory?
        if name in current_server_dirs:
            return current_server_dirs[name]

        def parse_directory(name):
            matches = re.match(ls_regex, name)
            if matches:
                if not name.startswith('d'):
                    return False # indicates not directory (ie file)
                directory = _ls_matches_to_dict(matches)
                return directory

        logger.info('Running directory fact on {}'.format(colored(name, attrs=['bold'])))
        outs = run_all_command('ls -ldp {0}'.format(name), join_output=True)

        # Assign all & return current
        _assign_facts(outs, name, parse_directory, '_dirs')
        return pyinfra._facts[pyinfra._current_server]['_dirs'][name]

    def file(self, name):
        '''Like a fact, but for file information.'''
        current_server_files = pyinfra._facts[pyinfra._current_server]['_files']

        # Already got this file?
        if name in current_server_files:
            return current_server_files[name]

        def parse_file(name):
            matches = re.match(ls_regex, name)
            if matches:
                if name.startswith('d'):
                    return False # indicates not file (ie dir)
                return _ls_matches_to_dict(matches)

        logger.info('Running file fact on {}'.format(colored(name, attrs=['bold'])))
        outs = run_all_command('ls -ldp {0}'.format(name), join_output=True)

        # Assign & return current
        _assign_facts(outs, name, parse_file, '_files')
        return pyinfra._facts[pyinfra._current_server]['_files'][name]


# Swap out this module with a Host instance
# also add to pyinfra's global namespace for use in deploy scripts (pyinfra.api.server implies internal usage)
pyinfra.host = Host()
