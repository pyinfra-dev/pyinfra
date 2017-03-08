# pyinfra
# File: pyinfra/cli/prints.py
# Desc: print utilities for the CLI

from __future__ import print_function, unicode_literals

import json
import traceback

import six

from termcolor import colored

from pyinfra import logger
from pyinfra.api.facts import get_fact_names

from . import json_encode


def print_facts_list():
    print(json.dumps(list(get_fact_names()), indent=4, default=json_encode))


def print_fact(fact_data):
    print(json.dumps(fact_data, indent=4, default=json_encode))


def dump_trace(exc_info):
    # Dev mode, so lets dump as much data as we have
    error_type, value, trace = exc_info
    print('----------------------')
    traceback.print_tb(trace)
    logger.critical('{0}: {1}'.format(error_type.__name__, value))
    print('----------------------')


def dump_state(state):
    print()
    print('--> Gathered facts:')
    print(json.dumps(state.facts, indent=4, default=json_encode))
    print()
    print('--> Proposed operations:')
    print(json.dumps(state.ops, indent=4, default=json_encode))
    print()
    print('--> Operation meta:')
    print(json.dumps(state.op_meta, indent=4, default=json_encode))
    print()
    print('--> Operation order:')
    print(json.dumps(state.op_order, indent=4, default=json_encode))


def print_inventory(inventory):
    for host in inventory:
        print('[{0}]'.format(colored(host.name, attrs=['bold'])))
        print(json.dumps(host.data.dict(), indent=4, default=json_encode))
        print()


def get_group_combinations(inventory):
    group_combinations = {}

    for host in inventory.iter_all_hosts():
        # Tuple for hashability, set to normalise order
        host_groups = tuple(set(host.groups))

        group_combinations.setdefault(host_groups, [])
        group_combinations[host_groups].append(host)

    return group_combinations


def print_meta(state, inventory):
    group_combinations = get_group_combinations(inventory)

    for i, (groups, hosts) in enumerate(six.iteritems(group_combinations), 1):
        if groups:
            logger.info('Groups: {0}'.format(
                colored(' / '.join(groups), attrs=['bold']),
            ))
        else:
            logger.info('Ungrouped')

        for host in hosts:
            meta = state.meta[host.name]

            # Didn't connect to this host?
            if host.name not in state.connected_hosts:
                logger.info('[{0}]\tNo connection'.format(
                    colored(host.name, 'red', attrs=['bold']),
                ))
                continue

            logger.info(
                '[{0}]\tOperations: {1}\t    Commands: {2}'.format(
                    colored(host.name, attrs=['bold']),
                    meta['ops'], meta['commands'],
                ),
            )

        if i != len(group_combinations):
            print()


def print_results(state, inventory):
    group_combinations = get_group_combinations(inventory)

    for i, (groups, hosts) in enumerate(six.iteritems(group_combinations), 1):
        logger.info('Groups: {0}'.format(
            colored(' / '.join(groups), attrs=['bold']),
        ))

        for host in hosts:
            # Didn't conenct to this host?
            if host.name not in state.connected_hosts:
                logger.info('[{0}]\tNo connection'.format(
                    colored(host.name, 'red', attrs=['bold']),
                ))
                continue

            results = state.results[host.name]

            meta = state.meta[host.name]
            success_ops = results['success_ops']
            error_ops = results['error_ops']

            # If all ops got complete (even with ignored_errors)
            if results['ops'] == meta['ops']:
                # Yellow if ignored any errors, else green
                color = 'green' if error_ops == 0 else 'yellow'
                host_string = colored(host.name, color)

            # Ops did not complete!
            else:
                host_string = colored(host.name, 'red', attrs=['bold'])

            logger.info('[{0}]\tSuccessful: {1}\t    Errors: {2}\t    Commands: {3}/{4}'.format(
                host_string,
                colored(success_ops, attrs=['bold']),
                error_ops
                if error_ops == 0
                else colored(error_ops, 'red', attrs=['bold']),
                results['commands'], meta['commands'],
            ))

        if i != len(group_combinations):
            print()
