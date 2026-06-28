from __future__ import annotations

import json
import platform
import re
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union, cast
from collections.abc import Callable, Iterator

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
    group_combinations: dict[tuple, list[Host]] = {}

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


def print_json(payload) -> None:
    click.echo(jsonify(payload, default=json_encode))


def _host_to_dict(host: Host) -> dict:
    """
    Serialise a host for ``debug-inventory --json``.

    ``data`` is the host's inventory data passed through as-is. It is
    dumped by ``print_json`` (with ``json_encode`` as the fallback
    encoder), so any value that is neither natively JSON-serialisable nor
    handled by ``json_encode`` (arbitrary Python objects, etc.) will raise
    when the payload is written. Keep inventory data JSON-friendly when
    you intend to consume this output.
    """
    return {
        "name": host.name,
        "groups": list(host.groups),
        "data": host.data,
    }


def print_inventory_json(state: State) -> None:
    print_json([_host_to_dict(host) for host in state.inventory])


def print_facts_json(fact_data: dict) -> None:
    print_json(fact_data)


def print_state_operations_json(state: State) -> None:
    state_ops = {host: ops for host, ops in state.ops.items() if state.is_host_in_limit(host)}
    payload = {
        "operations": state_ops,
        "op_meta": state.op_meta,
        "op_order": [
            {
                "op_hash": op_hash,
                "names": sorted(state.op_meta[op_hash].names),
                "hosts": sorted(host.name for host, ops in state.ops.items() if op_hash in ops),
            }
            for op_hash in state.get_op_order()
        ],
    }
    print_json(payload)


def build_plan_json(state: State) -> list[dict]:
    operations: list[dict] = []
    for op_hash in state.get_op_order():
        hosts_in_op: list[str] = []
        hosts_maybe_in_op: list[str] = []
        for host in state.inventory.iter_activated_hosts():
            if op_hash not in state.ops[host]:
                continue
            op_data = state.get_op_data_for_host(host, op_hash)
            if not op_data.operation_meta._maybe_is_change:
                continue
            if op_data.global_arguments["_if"]:
                hosts_maybe_in_op.append(host.name)
            else:
                hosts_in_op.append(host.name)

        meta = state.op_meta[op_hash]
        operations.append(
            {
                "op_hash": op_hash,
                "name": pretty_op_name(meta),
                "names": sorted(meta.names),
                "args": list(meta.args),
                "hosts_with_change": sorted(hosts_in_op),
                "hosts_with_conditional_change": sorted(hosts_maybe_in_op),
            }
        )
    return operations


def build_results_json(state: State) -> dict:
    operations: list[dict] = []
    totals = {"hosts": 0, "success": 0, "error": 0, "no_change": 0}

    for op_hash in state.get_op_order():
        hosts_in_op = 0
        success: list[str] = []
        error: list[str] = []
        no_change: list[str] = []

        for host in state.inventory.iter_activated_hosts():
            if op_hash not in state.ops[host]:
                continue

            hosts_in_op += 1
            op_meta = state.ops[host][op_hash].operation_meta
            if op_meta.did_succeed(_raise_if_not_complete=False):
                if op_meta.did_change():
                    success.append(host.name)
                else:
                    no_change.append(host.name)
            else:
                error.append(host.name)

        meta = state.op_meta[op_hash]
        operations.append(
            {
                "op_hash": op_hash,
                "name": pretty_op_name(meta),
                "names": sorted(meta.names),
                "args": list(meta.args),
                "hosts": hosts_in_op,
                "success": sorted(success),
                "error": sorted(error),
                "no_change": sorted(no_change),
            }
        )

        totals["hosts"] += hosts_in_op
        totals["success"] += len(success)
        totals["error"] += len(error)
        totals["no_change"] += len(no_change)

    return {
        "operations": operations,
        "totals": totals,
        "failed_hosts": sorted(host.name for host in state.failed_hosts),
    }


def print_run_json(state: State, dry: bool) -> None:
    payload: dict = {"plan": build_plan_json(state)}
    if dry:
        payload["results"] = None
    else:
        payload["results"] = build_results_json(state)
    print_json(payload)


def print_state_operations(state: State):
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
            f"    {op_hash} (names={meta.names}, hosts={hosts})",
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
                f"    {', '.join(click.style(name, bold=True) for name in items)}",
                err=True,
            )

            items = [name]

        last_name = name

    if items:
        click.echo(
            f"    {', '.join(click.style(name, bold=True) for name in items)}",
            err=True,
        )


def print_fact(fact_data):
    click.echo(jsonify(fact_data, indent=4, default=json_encode), err=True)


def print_inventory(state: State):
    for host in state.inventory:
        click.echo(err=True)
        click.echo(host.print_prefix, err=True)
        click.echo(f"--> Groups: {', '.join(host.groups)}", err=True)
        click.echo("--> Data:", err=True)
        click.echo(jsonify(host.data, indent=4, default=json_encode), err=True)


def print_facts(facts):
    for name, data in facts.items():
        click.echo(err=True)
        click.echo(
            f"--> Fact data for: {click.style(name, bold=True)}",
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

    click.echo(f"    System: {platform.system()}", err=True)
    click.echo(f"      Platform: {platform.platform()}", err=True)
    click.echo(f"      Release: {platform.uname()[2]}", err=True)
    click.echo(f"      Machine: {platform.uname()[4]}", err=True)
    click.echo(f"    pyinfra: v{__version__}", err=True)

    seen_reqs: set[str] = set()
    for requirement_string in sorted(requires("pyinfra") or []):
        requirement = Requirement(requirement_string)
        if requirement.name in seen_reqs:
            continue
        seen_reqs.add(requirement.name)
        try:
            click.echo(
                f"      {requirement.name}: v{version(requirement.name)}",
                err=True,
            )
        except PackageNotFoundError:
            # package not installed in this environment
            continue

    click.echo(f"    Executable: {sys.argv[0]}", err=True)
    click.echo(
        f"    Python: {platform.python_version()} ({platform.python_implementation()}, {platform.python_compiler()})",
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
                    f"{column}{' '.join('' for _ in range(padding))}",
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
        name = f"{name} ({', '.join(str(arg) for arg in op_meta.args)})"

    return name


def print_meta(state: State):
    rows: list[tuple[Callable, list[str] | str]] = [
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
                        else f"{len(hosts_in_op)} ({truncate(', '.join(sorted(hosts_in_op)), 48)})"
                    ),
                    (
                        "-"
                        if len(hosts_maybe_in_op) == 0
                        else f"{len(hosts_maybe_in_op)} ({truncate(', '.join(sorted(hosts_maybe_in_op)), 48)})"
                    ),
                ],
            )
        )

    print_rows(rows)


def print_results(state: State):
    rows: list[tuple[Callable, list[str] | str]] = [
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


def _format_seconds(seconds: float) -> str:
    if seconds >= 60:
        minutes, secs = divmod(seconds, 60)
        return "{0:d}m {1:.2f}s".format(int(minutes), secs)
    if seconds >= 1:
        return "{0:.2f}s".format(seconds)
    return "{0:.0f}ms".format(seconds * 1000)


def print_run_elapsed(state: "State"):
    elapsed = state.timings.elapsed
    if elapsed is None:
        return
    click.echo(err=True)
    click.echo("--> Finished, took {0}".format(_format_seconds(elapsed)), err=True)


def _collect_op_timings(state: "State", top_n: int = 10) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for op_hash in state.get_op_order():
        prepare = state.timings.op_prepare.get(op_hash, {})
        execute = state.timings.op_execute.get(op_hash, {})
        if not prepare and not execute:
            continue
        total_prepare = sum(prepare.values())
        total_execute = sum(execute.values())
        max_execute = max(execute.values()) if execute else 0.0
        rows.append(
            {
                "op_hash": op_hash,
                "name": pretty_op_name(state.op_meta[op_hash]),
                "total_prepare_seconds": total_prepare,
                "total_execute_seconds": total_execute,
                "max_host_execute_seconds": max_execute,
                "hosts_executed": len(execute),
            }
        )
    rows.sort(key=lambda r: cast(float, r["total_execute_seconds"]), reverse=True)
    return rows[:top_n]


def _collect_fact_timings(state: "State", top_n: int = 10) -> List[Dict[str, Any]]:
    aggregated: Dict[str, Dict[str, float]] = {}
    for host_facts in state.timings.facts.values():
        for fact_key, samples in host_facts.items():
            entry = aggregated.setdefault(
                fact_key,
                {"total": 0.0, "max": 0.0, "samples": 0, "hosts": 0},
            )
            entry["total"] += sum(samples)
            entry["max"] = max(entry["max"], max(samples))
            entry["samples"] += len(samples)
            entry["hosts"] += 1

    rows: List[Dict[str, Any]] = [
        {
            "fact": fact_key,
            "total_seconds": data["total"],
            "max_host_seconds": data["max"],
            "samples": int(data["samples"]),
            "hosts": int(data["hosts"]),
        }
        for fact_key, data in aggregated.items()
    ]
    rows.sort(key=lambda r: cast(float, r["total_seconds"]), reverse=True)
    return rows[:top_n]


def print_timings(state: "State", top_n: int = 10):
    """
    Print a human-readable summary of the slowest operations and facts.
    """
    op_rows = _collect_op_timings(state, top_n=top_n)
    fact_rows = _collect_fact_timings(state, top_n=top_n)

    click.echo(err=True)
    click.echo("--> Timings:", err=True)

    if op_rows:
        rows: List[Tuple[Callable, Union[List[str], str]]] = [
            (
                logger.info,
                ["Operation", "Hosts", "Prepare (sum)", "Execute (sum)", "Slowest host"],
            ),
        ]
        for r in op_rows:
            rows.append(
                (
                    logger.info,
                    [
                        truncate(r["name"], 60),
                        str(r["hosts_executed"]),
                        _format_seconds(r["total_prepare_seconds"]),
                        _format_seconds(r["total_execute_seconds"]),
                        _format_seconds(r["max_host_execute_seconds"]),
                    ],
                )
            )
        print_rows(rows)
    else:
        click.echo("    No operation timings recorded.", err=True)

    click.echo(err=True)

    if fact_rows:
        rows = [
            (logger.info, ["Fact", "Hosts", "Calls", "Total", "Slowest"]),
        ]
        for r in fact_rows:
            rows.append(
                (
                    logger.info,
                    [
                        truncate(r["fact"], 60),
                        str(r["hosts"]),
                        str(r["samples"]),
                        _format_seconds(r["total_seconds"]),
                        _format_seconds(r["max_host_seconds"]),
                    ],
                )
            )
        print_rows(rows)
    else:
        click.echo("    No fact timings recorded.", err=True)


def print_timings_json(state: "State"):
    """
    Print a JSON document with structured timing data to stdout. Designed for
    consumption by external tooling.
    """
    payload = {
        "wall_start": state.timings.wall_start,
        "wall_end": state.timings.wall_end,
        "elapsed_seconds": state.timings.elapsed,
        "operations": [
            {
                "op_hash": op_hash,
                "name": pretty_op_name(state.op_meta[op_hash]),
                "prepare": {
                    host.name: seconds
                    for host, seconds in state.timings.op_prepare.get(op_hash, {}).items()
                },
                "execute": {
                    host.name: seconds
                    for host, seconds in state.timings.op_execute.get(op_hash, {}).items()
                },
            }
            for op_hash in state.get_op_order()
            if op_hash in state.timings.op_prepare or op_hash in state.timings.op_execute
        ],
        "facts": {
            host.name: {fact_key: list(samples) for fact_key, samples in host_facts.items()}
            for host, host_facts in state.timings.facts.items()
        },
    }
    click.echo(json.dumps(payload, indent=2, default=json_encode))
