from __future__ import unicode_literals

import json
import platform
import re
import sys

import click
import six

from pyinfra import __version__, logger
from pyinfra.api.facts import get_fact_names
from pyinfra.api.host import Host
from pyinfra.api.operation import get_operation_names

from .util import json_encode

ANSI_RE = re.compile(r'\033\[((?:\d|;)*)([a-zA-Z])')


def _strip_ansi(value):
    return ANSI_RE.sub('', value)


def _get_group_combinations(inventory):
    group_combinations = {}

    for host in inventory:
        # Tuple for hashability, set to normalise order
        host_groups = tuple(set(host.groups))

        group_combinations.setdefault(host_groups, [])
        group_combinations[host_groups].append(host)

    return group_combinations


def _stringify_host_keys(data):
    if isinstance(data, dict):
        return {
            key.name if isinstance(key, Host) else key: _stringify_host_keys(value)
            for key, value in six.iteritems(data)
        }

    return data


def jsonify(data, *args, **kwargs):
    data = _stringify_host_keys(data)
    return json.dumps(data, *args, **kwargs)


def print_state_facts(state):
    click.echo(err=True)
    click.echo('--> Facts:', err=True)
    click.echo(jsonify(state.facts, indent=4, default=json_encode), err=True)


def print_state_operations(state):
    state_ops = {
        host: ops
        for host, ops in state.ops.items()
        if state.is_host_in_limit(host)
    }

    click.echo(err=True)
    click.echo('--> Operations:', err=True)
    click.echo(jsonify(state_ops, indent=4, default=json_encode), err=True)
    click.echo(err=True)
    click.echo('--> Operation meta:', err=True)
    click.echo(jsonify(state.op_meta, indent=4, default=json_encode), err=True)

    click.echo(err=True)
    click.echo('--> Operation order:', err=True)
    click.echo(err=True)
    for op_hash in state.get_op_order():
        meta = state.op_meta[op_hash]
        hosts = set(
            host for host, operations in six.iteritems(state.ops)
            if op_hash in operations
        )

        click.echo('    {0} (names={1}, hosts={2})'.format(
            op_hash, meta['names'], hosts,
        ), err=True)


def print_groups_by_comparison(print_items, comparator=lambda item: item[0]):
    items = []
    last_name = None

    for name in print_items:
        # Keep all facts with the same first character on one line
        if last_name is None or comparator(last_name) == comparator(name):
            items.append(name)

        else:
            click.echo('    {0}'.format(', '.join((
                click.style(name, bold=True)
                for name in items
            ))), err=True)

            items = [name]

        last_name = name

    if items:
        click.echo('    {0}'.format(', '.join((
            click.style(name, bold=True)
            for name in items
        ))), err=True)


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
    click.echo(jsonify(fact_data, indent=4, default=json_encode), err=True)


def print_inventory(state):
    for host in state.inventory:
        click.echo(err=True)
        click.echo(host.print_prefix, err=True)
        click.echo('--> Groups: {0}'.format(', '.join(host.groups)), err=True)
        click.echo('--> Data:', err=True)
        click.echo(jsonify(host.data, indent=4, default=json_encode), err=True)


def print_facts(facts):
    for name, data in six.iteritems(facts):
        click.echo(err=True)
        click.echo('--> Fact data for: {0}'.format(
            click.style(name, bold=True),
        ), err=True)
        print_fact(data)


def print_support_info():
    click.echo('''
    If you are having issues with pyinfra or wish to make feature requests, please
    check out the GitHub issues at https://github.com/Fizzadar/pyinfra/issues .
    When adding an issue, be sure to include the following:
''')

    click.echo('    System: {0}'.format(platform.system()), err=True)
    click.echo('      Platform: {0}'.format(platform.platform()), err=True)
    click.echo('      Release: {0}'.format(platform.uname()[2]), err=True)
    click.echo('      Machine: {0}'.format(platform.uname()[4]), err=True)
    click.echo('    pyinfra: v{0}'.format(__version__), err=True)
    click.echo('    Executable: {0}'.format(sys.argv[0]), err=True)
    click.echo('    Python: {0} ({1}, {2})'.format(
        platform.python_version(),
        platform.python_implementation(),
        platform.python_compiler(),
    ), err=True)


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


def print_meta(state):
    group_combinations = _get_group_combinations(state.inventory.iter_activated_hosts())
    rows = []

    for i, (groups, hosts) in enumerate(six.iteritems(group_combinations), 1):
        if not hosts:
            continue

        if groups:
            rows.append((logger.info, 'Groups: {0}'.format(
                click.style(' / '.join(groups), bold=True),
            )))
        else:
            rows.append((logger.info, 'Ungrouped:'))

        for host in hosts:
            meta = state.meta[host]

            # Didn't connect to this host?
            if host not in state.activated_hosts:
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
            rows.append((lambda m: click.echo(m, err=True), []))

    print_rows(rows)


def print_results(state):
    group_combinations = _get_group_combinations(state.inventory.iter_activated_hosts())
    rows = []

    for i, (groups, hosts) in enumerate(six.iteritems(group_combinations), 1):
        if not hosts:
            continue

        if groups:
            rows.append((logger.info, 'Groups: {0}'.format(
                click.style(' / '.join(groups), bold=True),
            )))
        else:
            rows.append((logger.info, 'Ungrouped:'))

        for host in hosts:
            # Didn't connect to this host?
            if host not in state.activated_hosts:
                rows.append((logger.info, [
                    host.style_print_prefix('red', bold=True),
                    click.style('No connection', 'red'),
                ]))
                continue

            results = state.results[host]

            meta = state.meta[host]
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
            rows.append((lambda m: click.echo(m, err=True), []))

    print_rows(rows)
