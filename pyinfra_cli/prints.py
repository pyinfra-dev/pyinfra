# pyinfra
# File: pyinfra_cli/prints.py
# Desc: print utilities for the CLI

from __future__ import print_function, unicode_literals

import json
import re
import traceback

import click
import six

from pyinfra import logger
from pyinfra.api.facts import get_fact_names
from pyinfra.api.operation import get_operation_names

from .util import json_encode

ANSI_RE = re.compile('\033\[((?:\d|;)*)([a-zA-Z])')


def _strip_ansi(value):
    return ANSI_RE.sub('', value)


def _get_group_combinations(inventory):
    group_combinations = {}

    for host in inventory.iter_all_hosts():
        # Tuple for hashability, set to normalise order
        host_groups = tuple(set(host.groups))

        group_combinations.setdefault(host_groups, [])
        group_combinations[host_groups].append(host)

    return group_combinations


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


def print_groups_by_comparison(print_items, comparator=lambda item: item[0]):
    items = []
    last_name = None

    for name in print_items:
        # Keep all facts with the same first character on one line
        if last_name is None or comparator(last_name) == comparator(name):
            items.append(name)

        else:
            print('    {0}'.format(', '.join((
                click.style(name, bold=True)
                for name in items
            ))))

            items = [name]

        last_name = name

    if items:
        print('    {0}'.format(', '.join((
            click.style(name, bold=True)
            for name in items
        ))))


def print_facts_list():
    fact_names = sorted(get_fact_names())
    print_groups_by_comparison(fact_names)


def print_operations_list():
    operation_names = sorted(get_operation_names())
    print_groups_by_comparison(
        operation_names,
        comparator=lambda item: item.split('.')[0],
    )


def print_fact(fact_data):
    print(json.dumps(fact_data, indent=4, default=json_encode))


def print_inventory(inventory):
    for host in inventory:
        print()
        print('--> Data for: {0}'.format(click.style(host.name, bold=True)))
        print(json.dumps(host.data.dict(), indent=4, default=json_encode))


def print_facts(facts):
    for name, data in six.iteritems(facts):
        print()
        print('--> Fact data for: {0}'.format(
            click.style(name, bold=True),
        ))
        print_fact(data)


def print_rows(rows):
    # Go through the rows and work out all the widths in each column
    column_widths = []

    for _, columns in rows:
        if isinstance(columns, six.string_types):
            continue

        for i, column in enumerate(columns):
            if i >= len(column_widths):
                column_widths.append([])

            # Length of the column (with ansi codes removed)
            width = len(_strip_ansi(column.strip()))
            column_widths[i].append(width)

    # Get the max width of each column and add 4 padding spaces
    column_widths = [
        max(widths) + 4
        for widths in column_widths
    ]

    # Now print each column, keeping text justified to the widths above
    for func, columns in rows:
        line = columns

        if not isinstance(columns, six.string_types):
            justified = []

            for i, column in enumerate(columns):
                stripped = _strip_ansi(column)
                desired_width = column_widths[i]
                padding = desired_width - len(stripped)

                justified.append('{0}{1}'.format(
                    column, ' '.join('' for _ in range(padding)),
                ))

            line = ''.join(justified)

        func(line)


def print_meta(state, inventory):
    group_combinations = _get_group_combinations(inventory)
    rows = []

    for i, (groups, hosts) in enumerate(six.iteritems(group_combinations), 1):
        if groups:
            rows.append((logger.info, 'Groups: {0}'.format(
                click.style(' / '.join(groups), bold=True),
            )))
        else:
            rows.append((logger.info, 'Ungrouped:'))

        for host in hosts:
            meta = state.meta[host.name]

            # Didn't connect to this host?
            if host.name not in state.connected_host_names:
                rows.append((logger.info, [
                    host.style_print_prefix('red', bold=True),
                    click.style('No connection', 'red'),
                ]))
                continue

            rows.append((logger.info, [
                host.print_prefix,
                'Operations: {0}'.format(meta['ops']),
                'Commands: {0}'.format(meta['commands']),
            ]))

        if i != len(group_combinations):
            rows.append((print, []))

    print_rows(rows)


def print_results(state, inventory):
    group_combinations = _get_group_combinations(inventory)
    rows = []

    for i, (groups, hosts) in enumerate(six.iteritems(group_combinations), 1):
        if groups:
            rows.append((logger.info, 'Groups: {0}'.format(
                click.style(' / '.join(groups), bold=True),
            )))
        else:
            rows.append((logger.info, 'Ungrouped:'))

        for host in hosts:
            # Didn't conenct to this host?
            if host.name not in state.connected_host_names:
                rows.append((logger.info, [
                    host.style_print_prefix('red', bold=True),
                    click.style('No connection', 'red'),
                ]))
                continue

            results = state.results[host.name]

            meta = state.meta[host.name]
            success_ops = results['success_ops']
            error_ops = results['error_ops']

            host_args = ('green',)
            host_kwargs = {}

            # If all ops got complete
            if results['ops'] == meta['ops']:
                # We had some errors - but we ignored them - so "warning" color
                if error_ops != 0:
                    host_args = ('yellow',)

            # Ops did not complete!
            else:
                host_args = ('red',)
                host_kwargs['bold'] = True

            rows.append((logger.info, [
                host.style_print_prefix(*host_args, **host_kwargs),
                'Successful: {0}'.format(click.style(six.text_type(success_ops), bold=True)),
                'Errors: {0}'.format(click.style(six.text_type(error_ops), bold=True)),
                'Commands: {0}/{1}'.format(results['commands'], meta['commands']),
            ]))

        if i != len(group_combinations):
            rows.append((print, []))

    print_rows(rows)
