# pyinfra
# File: pyinfra/api/server.py
# Desc: used via `pyinfra.server` in modules
#       peeds up gather_facts by doing them for every host when requested on one, in parallel

import re
import sys

import pyinfra
from pyinfra import logger
from .facts import FACTS
from .ssh import run_command

# Get & return all facts
def all_facts():
    for key in FACTS:
        fact(key)

    return pyinfra._facts[pyinfra._current_server]

# Get a fact
def fact(key):
    if key not in FACTS:
        logger.critical('Missing fact: {0}'.format(key))
        sys.exit(1)

    current_server_facts = pyinfra._facts[pyinfra._current_server]

    # Already got this fact?
    if key in current_server_facts:
        return current_server_facts[key]

    logger.info('Running fact {0}...'.format(key))
    # For each server, spawn a job on the pool to gather the fact
    outs = run_command(FACTS[key].command)

    # Process & assign each fact
    for (server, stdout, stderr) in outs:
        result = FACTS[key].process(stdout.read())
        pyinfra._facts[server][key] = result
        logger.debug('Fact {0} for {1} assigned to {2}'.format(key, server, result))

    # Join, cache in _facts
    return pyinfra._facts[pyinfra._current_server][key]


# Regex to parse ls -ldp output
ls_regex = r'[a-z-]?([-rwx]{9})\.? [0-9]+ ([a-zA-Z]+) ([a-zA-Z]+) ([0-9]+) [a-zA-Z]{3} [0-9]+ [0-9]{2}:[0-9]{2} (.*)\r'

def _matches_to_dict(matches):
    # Parse permissions into octal format (which is what we compare to deploy scripts)
    def parse_permissions(permissions):
        result = ''
        # owner, group, world
        for group in [permissions[0:3], permissions[3:6], permissions[6:9]]:
            if group == 'rwx':
                result += '7'
            elif group == 'rw-':
                result += '6'
            elif group == 'r-x':
                result += '5'
            elif group == 'r--':
                result += '4'
            elif group == '-wx':
                result += '3'
            elif group == '-w-':
                result += '2'
            elif group == '--x':
                result += '1'
            else:
                result += '0'

        return result

    return {
        'permissions': parse_permissions(matches.group(1)),
        'user': matches.group(2),
        'group': matches.group(3),
        'size': matches.group(4)
    }

# Get directory details
def directory(name):
    current_server_dirs = pyinfra._facts[pyinfra._current_server]['_dirs']

    # Already got this directory?
    if name in current_server_dirs:
        return current_server_dirs[name]

    def parse_directory(name):
        matches = re.search(ls_regex, name)
        if matches:
            if not name.startswith('d'):
                return False # indicates not directory (ie file)
            return _matches_to_dict(matches)

    logger.info('Running directory fact on {0}...'.format(name))
    outs = run_command('ls -ldp {0}'.format(name))
    for (server, stdout, stderr) in outs:
        directory = parse_directory(stdout.read())
        pyinfra._facts[server]['_dirs'][name] = directory
        logger.debug('Directory {0} for {1} assigned to {2}'.format(name, server, directory))

    return pyinfra._facts[pyinfra._current_server]['_dirs'][name]


# Get file details
def file(name):
    current_server_files = pyinfra._facts[pyinfra._current_server]['_files']

    # Already got this file?
    if name in current_server_files:
        return current_server_files[name]

    def parse_file(name):
        matches = re.search(ls_regex, name)
        if matches:
            if name.startswith('d'):
                return False # indicates not file (ie dir)
            return _matches_to_dict(matches)

    logger.debug('Running file fact on {0}...'.format(name))
    outs = run_command('ls -ldp {0}'.format(name))
    for (server, stdout, stderr) in outs:
        file = parse_file(stdout.read())
        pyinfra._facts[server]['_files'][name] = file
        logger.debug('File {0} for {1} assigned to {2}'.format(name, server, file))

    return pyinfra._facts[pyinfra._current_server]['_files'][name]
