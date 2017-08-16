#!/usr/bin/env python

# pyinfra
# File: scripts/generate_empty_tests.py
# Desc: generate empty test files

from __future__ import print_function

import json
import sys

from os import makedirs, path

from pyinfra.api.facts import get_fact_names
from pyinfra.api.operation import get_operation_names

WRITE_EMPTIES = '--write' in sys.argv
WRITE_LIMIT = [
    item for item in sys.argv[1:]
    if item != '--write'
]

EMPTY_FACT = '{0}\n'.format(json.dumps({
    'output': [],
    'fact': None,
}, indent=4))

EMPTY_OPERATION = '{0}\n'.format(json.dumps({
    'args': [],
    'kwargs': {},
    'facts': {},
    'commands': [],
    'exception': {},
}, indent=4))


print('--> {0} empty fact tests'.format(
    'Generating' if WRITE_EMPTIES else 'Printing',
))
for fact in get_fact_names():
    if WRITE_LIMIT and fact not in WRITE_LIMIT:
        continue

    fact_folder = path.join('tests', 'facts', fact)

    if not path.exists(fact_folder):
        fact_file = path.join(fact_folder, 'empty.json')

        if WRITE_EMPTIES:
            makedirs(fact_folder)
            f = open(fact_file, 'w')
            f.write(EMPTY_FACT)
            f.close()

        print('    {0}: {1}'.format(
            'written' if WRITE_EMPTIES else 'missing',
            fact_file,
        ))


print()
print('--> {0} empty operation tests'.format(
    'Generating' if WRITE_EMPTIES else 'Printing',
))
for operation in get_operation_names():
    if WRITE_LIMIT and operation not in WRITE_LIMIT:
        continue

    operation_folder = path.join('tests', 'operations', operation)
    if not path.exists(operation_folder):
        operation_file = path.join(operation_folder, 'empty.json')

        if WRITE_EMPTIES:
            makedirs(operation_folder)
            f = open(operation_file, 'w')
            f.write(EMPTY_OPERATION)
            f.close()

        print('    {0}: {1}'.format(
            'written' if WRITE_EMPTIES else 'missing',
            operation_file,
        ))

print()
print('--> Done!')
