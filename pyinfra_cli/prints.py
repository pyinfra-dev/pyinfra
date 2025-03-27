from __future__ import annotations

import json
import platform
import re
import sys
from typing import TYPE_CHECKING, Callable, Dict, Iterator, List, Tuple, Union

import click

from pyinfra import __version__, logger
from pyinfra.api.host import Host

from .util import json_encode

if TYPE_CHECKING:
    from pyinfra.api.state import State


ANSI_RE = re.compile(r"\033\[((?:\d|;)*)([a-zA-Z])")


def _strip_ansi(value):
    return ANSI_RE.sub("", value)


def _get_group_combinations(inventory: Iterator[Host]):
    group_combinations: Dict[Tuple, List[Host]] = {}

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
            for key, value in data.items()
        }

    return data


def jsonify(data, *args, **kwargs):
    data = _stringify_host_keys(data)
    return json.dumps(data, *args, **kwargs)


def print_state_operations(state: "State"):
    state_ops = {host: ops for host, ops in state.ops.items() if state.is_host_in_limit(host)}

    click.echo(err=True)
    click.echo("--> Operations:", err=True)
    click.echo(jsonify(state_ops, indent=4, default=json_encode), err=True)
    click.echo(err=True)
    click.echo("--> Operation meta:", err=True)
    click.echo(jsonify(state.op_meta, indent=4, default=json_encode), err=True)

    click.echo(err=True)
    click.echo("--> Operation order:", err=True)
    click.echo(err=True)
    for op_hash in state.get_op_order():
        meta = state.op_meta[op_hash]
        hosts = set(host for host, operations in state.ops.items() if op_hash in operations)

        click.echo(
            "    {0} (names={1}, hosts={2})".format(
                op_hash,
                meta.names,
                hosts,
            ),
            err=True,
        )


def print_groups_by_comparison(print_items, comparator=lambda item: item[0]):
    items = []
    last_name = None

    for name in print_items:
        # Keep all facts with the same first character on one line
        if last_name is None or comparator(last_name) == comparator(name):
            items.append(name)

        else:
            click.echo(
                "    {0}".format(", ".join((click.style(name, bold=True) for name in items))),
                err=True,
            )

            items = [name]

        last_name = name

    if items:
        click.echo(
            "    {0}".format(", ".join((click.style(name, bold=True) for name in items))),
            err=True,
        )


def print_fact(fact_data):
    click.echo(jsonify(fact_data, indent=4, default=json_encode), err=True)


def print_inventory(state: "State"):
    for host in state.inventory:
        click.echo(err=True)
        click.echo(host.print_prefix, err=True)
        click.echo("--> Groups: {0}".format(", ".join(host.groups)), err=True)
        click.echo("--> Data:", err=True)
        click.echo(jsonify(host.data, indent=4, default=json_encode), err=True)


def print_facts(facts):
    for name, data in facts.items():
        click.echo(err=True)
        click.echo(
            "--> Fact data for: {0}".format(
                click.style(name, bold=True),
            ),
            err=True,
        )
        print_fact(data)


def print_support_info() -> None:
    from importlib.metadata import PackageNotFoundError, requires, version

    from packaging.requirements import Requirement

    click.echo(
        """
    If you are having issues with pyinfra or wish to make feature requests, please
    check out the GitHub issues at https://github.com/Fizzadar/pyinfra/issues .
    When adding an issue, be sure to include the following:
""",
    )

    click.echo("    System: {0}".format(platform.system()), err=True)
    click.echo("      Platform: {0}".format(platform.platform()), err=True)
    click.echo("      Release: {0}".format(platform.uname()[2]), err=True)
    click.echo("      Machine: {0}".format(platform.uname()[4]), err=True)
    click.echo("    pyinfra: v{0}".format(__version__), err=True)

    for requirement_string in sorted(requires("pyinfra") or []):
        requirement = Requirement(requirement_string)
        try:
            click.echo(
                "      {0}: v{1}".format(requirement.name, version(requirement.name)),
                err=True,
            )
        except PackageNotFoundError:
            # package not installed in this environment
            continue

    click.echo("    Executable: {0}".format(sys.argv[0]), err=True)
    click.echo(
        "    Python: {0} ({1}, {2})".format(
            platform.python_version(),
            platform.python_implementation(),
            platform.python_compiler(),
        ),
        err=True,
    )


def print_rows(rows):
    # Go through the rows and work out all the widths in each column
    row_column_widths: list[list[int]] = []

    for _, columns in rows:
        if isinstance(columns, str):
            continue

        for i, column in enumerate(columns):
            if i >= len(row_column_widths):
                row_column_widths.append([])

            # Length of the column (with ansi codes removed)
            width = len(_strip_ansi(column.strip()))
            row_column_widths[i].append(width)

    # Get the max width of each column and add 4 padding spaces
    column_widths = [max(widths) + 4 for widths in row_column_widths]

    # Now print each column, keeping text justified to the widths above
    for func, columns in rows:
        line = columns

        if not isinstance(columns, str):
            justified = []

            for i, column in enumerate(columns):
                stripped = _strip_ansi(column)
                desired_width = column_widths[i]
                padding = desired_width - len(stripped)

                justified.append(
                    "{0}{1}".format(
                        column,
                        " ".join("" for _ in range(padding)),
                    ),
                )

            line = "".join(justified)

        func(line)


def truncate(text, max_length):
    if len(text) <= max_length:
        return text

    text = text[: max_length - 3]
    return f"{text}..."


def pretty_op_name(op_meta):
    name = list(op_meta.names)[0]

    if op_meta.args:
        name = "{0} ({1})".format(name, ", ".join(str(arg) for arg in op_meta.args))

    return name


def print_meta(state: "State"):
    rows: List[Tuple[Callable, Union[List[str], str]]] = [
        (logger.info, ["Operation", "Change", "Conditional Change"]),
    ]

    for op_hash in state.get_op_order():
        hosts_in_op = []
        hosts_maybe_in_op = []
        for host in state.inventory.iter_activated_hosts():
            if op_hash in state.ops[host]:
                op_data = state.get_op_data_for_host(host, op_hash)
                if op_data.operation_meta._maybe_is_change:
                    if op_data.global_arguments["_if"]:
                        hosts_maybe_in_op.append(host.name)
                    else:
                        hosts_in_op.append(host.name)

        rows.append(
            (
                logger.info,
                [
                    pretty_op_name(state.op_meta[op_hash]),
                    (
                        "-"
                        if len(hosts_in_op) == 0
                        else "{0} ({1})".format(
                            len(hosts_in_op),
                            truncate(", ".join(sorted(hosts_in_op)), 48),
                        )
                    ),
                    (
                        "-"
                        if len(hosts_maybe_in_op) == 0
                        else "{0} ({1})".format(
                            len(hosts_maybe_in_op),
                            truncate(", ".join(sorted(hosts_maybe_in_op)), 48),
                        )
                    ),
                ],
            )
        )

    print_rows(rows)


def print_results(state: "State"):
    rows: List[Tuple[Callable, Union[List[str], str]]] = [
        (logger.info, ["Operation", "Hosts", "Success", "Error", "No Change"]),
    ]

    totals = {"hosts": 0, "success": 0, "error": 0, "no_change": 0}

    for op_hash in state.get_op_order():
        hosts_in_op = 0
        hosts_in_op_success: list[str] = []
        hosts_in_op_error: list[str] = []
        hosts_in_op_no_change: list[str] = []
        for host in state.inventory.iter_activated_hosts():
            if op_hash not in state.ops[host]:
                continue

            hosts_in_op += 1

            op_meta = state.ops[host][op_hash].operation_meta
            if op_meta.did_succeed(_raise_if_not_complete=False):
                if op_meta.did_change():
                    hosts_in_op_success.append(host.name)
                else:
                    hosts_in_op_no_change.append(host.name)
            else:
                hosts_in_op_error.append(host.name)

        row = [
            pretty_op_name(state.op_meta[op_hash]),
            str(hosts_in_op),
        ]

        totals["hosts"] += hosts_in_op

        if hosts_in_op_success:
            num_hosts_in_op_success = len(hosts_in_op_success)
            row.append(str(num_hosts_in_op_success))
            totals["success"] += num_hosts_in_op_success
        else:
            row.append("-")

        if hosts_in_op_error:
            num_hosts_in_op_error = len(hosts_in_op_error)
            row.append(str(num_hosts_in_op_error))
            totals["error"] += num_hosts_in_op_error
        else:
            row.append("-")

        if hosts_in_op_no_change:
            num_hosts_in_op_no_change = len(hosts_in_op_no_change)
            row.append(str(num_hosts_in_op_no_change))
            totals["no_change"] += num_hosts_in_op_no_change
        else:
            row.append("-")

        rows.append((logger.info, row))

    totals_row = ["Grand total"] + [str(i) if i else "-" for i in totals.values()]
    rows.append((logger.info, totals_row))

    print_rows(rows)
