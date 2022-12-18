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


def print_state_facts(state: "State"):
    click.echo(err=True)
    click.echo("--> Facts:", err=True)
    click.echo(jsonify(state.facts, indent=4, default=json_encode), err=True)


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
                meta["names"],
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


def print_support_info():
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
    column_widths = []

    for _, columns in rows:
        if isinstance(columns, str):
            continue

        for i, column in enumerate(columns):
            if i >= len(column_widths):
                column_widths.append([])

            # Length of the column (with ansi codes removed)
            width = len(_strip_ansi(column.strip()))
            column_widths[i].append(width)

    # Get the max width of each column and add 4 padding spaces
    column_widths = [max(widths) + 4 for widths in column_widths]

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


def print_meta(state: "State"):
    group_combinations = _get_group_combinations(state.inventory.iter_activated_hosts())
    rows: List[Tuple[Callable, Union[List[str], str]]] = []

    for i, (groups, hosts) in enumerate(group_combinations.items(), 1):
        if not hosts:
            continue

        if groups:
            rows.append(
                (
                    logger.info,
                    "Groups: {0}".format(
                        click.style(" / ".join(groups), bold=True),
                    ),
                ),
            )
        else:
            rows.append((logger.info, "Ungrouped:"))

        for host in hosts:
            meta = state.meta[host]

            # Didn't connect to this host?
            if host not in state.activated_hosts:
                rows.append(
                    (
                        logger.info,
                        [
                            host.style_print_prefix("red", bold=True),
                            click.style("No connection", "red"),
                        ],
                    ),
                )
                continue

            rows.append(
                (
                    logger.info,
                    [
                        host.print_prefix,
                        "Operations: {0}".format(meta["ops"]),
                        "Change: {0}".format(meta["ops_change"]),
                        "No change: {0}".format(meta["ops_no_change"]),
                    ],
                ),
            )

        if i != len(group_combinations):
            rows.append((lambda m: click.echo(m, err=True), []))

    print_rows(rows)


def print_results(state: "State"):
    group_combinations = _get_group_combinations(state.inventory.iter_activated_hosts())
    rows: List[Tuple[Callable, Union[List[str], str]]] = []

    for i, (groups, hosts) in enumerate(group_combinations.items(), 1):
        if not hosts:
            continue

        if groups:
            rows.append(
                (
                    logger.info,
                    "Groups: {0}".format(
                        click.style(" / ".join(groups), bold=True),
                    ),
                ),
            )
        else:
            rows.append((logger.info, "Ungrouped:"))

        for host in hosts:
            # Didn't connect to this host?
            if host not in state.activated_hosts:
                rows.append(
                    (
                        logger.info,
                        [
                            host.style_print_prefix("red", bold=True),
                            click.style("No connection", "red"),
                        ],
                    ),
                )
                continue

            results = state.results[host]

            meta = state.meta[host]
            success_ops = results["success_ops"]
            partial_ops = results["partial_ops"]
            # TODO: type meta object
            changed_ops = success_ops - meta["ops_no_change"]  # type: ignore
            error_ops = results["error_ops"]
            ignored_error_ops = results["ignored_error_ops"]

            host_args = ("green",)
            host_kwargs = {}

            # If all ops got complete
            if results["ops"] == meta["ops"]:
                # We had some errors - but we ignored them - so "warning" color
                if error_ops != 0:
                    host_args = ("yellow",)

            # Ops did not complete!
            else:
                host_args = ("red",)
                host_kwargs["bold"] = True

            changed_str = "Changed: {0}".format(click.style(f"{changed_ops}", bold=True))
            if partial_ops:
                changed_str = f"{changed_str} ({partial_ops} partial)"

            error_str = "Errors: {0}".format(click.style(f"{error_ops}", bold=True))
            if ignored_error_ops:
                error_str = f"{error_str} ({ignored_error_ops} ignored)"

            rows.append(
                (
                    logger.info,
                    [
                        host.style_print_prefix(*host_args, **host_kwargs),
                        changed_str,
                        "No change: {0}".format(click.style(f"{meta['ops_no_change']}", bold=True)),
                        error_str,
                    ],
                ),
            )

        if i != len(group_combinations):
            rows.append((lambda m: click.echo(m, err=True), []))

    print_rows(rows)
