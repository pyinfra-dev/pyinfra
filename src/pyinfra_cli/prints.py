from __future__ import annotations

import json
import platform
import sys
from typing import TYPE_CHECKING, Any
from collections.abc import Iterator

from rich.console import Group
from rich.json import JSON
from rich.padding import Padding
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from pyinfra import __version__
from pyinfra.api.host import Host
from pyinfra.api.output import format_text

from . import routing
from .console import console, stdout_console
from .util import json_encode

if TYPE_CHECKING:
    from pyinfra.api.state import State


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


def _safe_encode(obj: Any) -> Any:
    """``json_encode`` fallback that never raises (for values).

    Used for the human ``debug-inventory`` rendering, where a value that is
    neither natively JSON-serialisable nor handled by ``json_encode`` (e.g. a
    compiled ``re.Pattern``) should degrade to its ``str()`` rather than
    aborting the whole command. The ``--json`` path keeps using the strict
    ``json_encode`` so machine output stays valid JSON.
    """
    try:
        return json_encode(obj)
    except TypeError:
        return str(obj)


def _json_safe_keys(value: Any) -> Any:
    """Recursively coerce non-primitive mapping keys to ``str``.

    ``json.dumps`` rejects dict keys that are not ``str``/``int``/``float``/
    ``bool``/``None`` *before* the ``default`` hook runs, so a ``re.Pattern``
    used as a ``fake_responses`` matcher key would still raise. This makes the
    human ``debug-inventory`` rendering robust against such keys.
    """
    if isinstance(value, dict):
        return {
            (key if isinstance(key, (str, int, float, bool)) or key is None else str(key)): (
                _json_safe_keys(val)
            )
            for key, val in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe_keys(item) for item in value]
    return value


def print_json(payload) -> None:
    json_str = jsonify(payload, default=json_encode)

    # When stdout is a real terminal, pretty-print + syntax-highlight the JSON.
    # When piped/redirected, emit plain JSON so it stays machine-parseable.
    if stdout_console.is_terminal:
        stdout_console.print(JSON(json_str))
    else:
        print(json_str)


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

    console.print()
    console.print("Operations:")
    console.print(jsonify(state_ops, indent=4, default=json_encode))
    console.print()
    console.print("Operation meta:")
    console.print(jsonify(state.op_meta, indent=4, default=json_encode))

    console.print()
    console.print("Operation order:")
    console.print()
    for op_hash in state.get_op_order():
        meta = state.op_meta[op_hash]
        hosts = set(host for host, operations in state.ops.items() if op_hash in operations)

        console.print(
            f"    {op_hash} (names={meta.names}, hosts={hosts})",
        )


def print_groups_by_comparison(print_items, comparator=lambda item: item[0]):
    items = []
    last_name = None

    for name in print_items:
        # Keep all facts with the same first character on one line
        if last_name is None or comparator(last_name) == comparator(name):
            items.append(name)

        else:
            console.print(
                f"    {', '.join(format_text(name, bold=True) for name in items)}",
            )

            items = [name]

        last_name = name

    if items:
        console.print(
            f"    {', '.join(format_text(name, bold=True) for name in items)}",
        )


def print_fact(fact_data):
    console.print(jsonify(fact_data, indent=4, default=json_encode))


def _scalar_style(value: Any) -> str:
    """Rich style for a scalar, matching the JSON highlighter's type colours.

    Non-JSON scalars (datetime, Path, ``re.Pattern``, arbitrary objects) render
    unstyled, since they are shown via ``str()`` rather than as JSON values.
    """
    # NOTE: bool is a subclass of int, so it must be checked first.
    if isinstance(value, bool):
        return "json.bool_true" if value else "json.bool_false"
    if value is None:
        return "json.null"
    if isinstance(value, (int, float)):
        return "json.number"
    if isinstance(value, str):
        return "json.str"
    return ""


def _format_host_data(data: dict) -> Group:
    """Render host data as one ``key: value`` line per top-level key.

    Scalars are shown inline; nested ``dict``/``list``/``tuple`` values are
    rendered as indented JSON (syntax-highlighted). Any other value (datetime,
    Path, ``re.Pattern``, arbitrary objects) falls back to ``str()`` so the
    display never fails on non-JSON-serialisable data. Insertion order is
    preserved.
    """
    if not data:
        return Group(Text("(no data)", style="dim"))

    lines: list[Any] = []
    for key, value in data.items():
        label = Text(f"{key}: ", style="bold blue")
        if isinstance(value, (dict, list, tuple)):
            # Nested structures: header line + indented JSON below it.
            lines.append(Text.assemble(label))
            value_json = jsonify(_json_safe_keys(value), indent=2, default=_safe_encode)
            lines.append(Padding(JSON(value_json), (0, 0, 0, 2)))
        else:
            # Scalars inline, coloured to match Rich's JSON highlighter (booleans
            # green/red, numbers cyan, null magenta, strings green). Other values
            # (datetime, Path, re.Pattern, arbitrary objects) fall back to an
            # unstyled str() so the display never fails on non-JSON data.
            lines.append(Text.assemble(label, (str(value), _scalar_style(value))))

    return Group(*lines)


def print_inventory(state: State):
    table = Table(
        title="Inventory",
        title_style="bold",
        header_style="bold",
        expand=True,
        leading=1,
    )
    # Only the data column flexes; host/groups stay as narrow as their content.
    table.add_column("Host", style="cyan", no_wrap=True, ratio=None)
    table.add_column("Groups", style="green", no_wrap=True, ratio=None)
    table.add_column("Data", ratio=1)

    for host in state.inventory:
        # A host may appear in the same group more than once (e.g. connector +
        # inventory group); de-duplicate for display while preserving order.
        groups = list(dict.fromkeys(host.groups))
        table.add_row(
            host.name,
            "\n".join(groups),
            _format_host_data(host.data.dict()),
        )

    console.print(table)


def print_facts(facts):
    for name, data in facts.items():
        console.print()
        console.print(
            f"Fact data for: {format_text(name, bold=True)}",
        )
        print_fact(data)


def print_support_info() -> None:
    from importlib.metadata import PackageNotFoundError, requires, version

    from packaging.requirements import Requirement

    console.print(
        """
    If you are having issues with pyinfra or wish to make feature requests, please
    check out the GitHub issues at https://github.com/Fizzadar/pyinfra/issues .
    When adding an issue, be sure to include the following:
""",
    )

    console.print(f"    System: {platform.system()}")
    console.print(f"      Platform: {platform.platform()}")
    console.print(f"      Release: {platform.uname()[2]}")
    console.print(f"      Machine: {platform.uname()[4]}")
    console.print(f"    pyinfra: v{__version__}")

    seen_reqs: set[str] = set()
    for requirement_string in sorted(requires("pyinfra") or []):
        requirement = Requirement(requirement_string)
        if requirement.name in seen_reqs:
            continue
        seen_reqs.add(requirement.name)
        try:
            console.print(
                f"      {requirement.name}: v{version(requirement.name)}",
            )
        except PackageNotFoundError:
            # package not installed in this environment
            continue

    console.print(f"    Executable: {sys.argv[0]}")
    console.print(
        f"    Python: {platform.python_version()} ({platform.python_implementation()}, {platform.python_compiler()})",
    )


def pretty_op_name(op_meta):
    name = list(op_meta.names)[0]

    if op_meta.args:
        name = f"{name} ({', '.join(str(arg) for arg in op_meta.args)})"

    return name


def _split_op_name(name: str) -> tuple[str | None, str]:
    """Split a "file.py | Operation" name into (file, operation)."""
    if " | " in name:
        filename, op_name = name.split(" | ", 1)
        return filename, op_name
    return None, name


def print_meta(state: State):
    tree = Tree(Text("Proposed changes", style="bold"), guide_style="dim")
    file_branches: dict[str, Any] = {}

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

        filename, op_name = _split_op_name(pretty_op_name(state.op_meta[op_hash]))

        parent = tree
        if filename is not None:
            branch = file_branches.get(filename)
            if branch is None:
                branch = tree.add(Text(filename, style="bold magenta"))
                file_branches[filename] = branch
            parent = branch

        n_change = len(hosts_in_op)
        n_maybe = len(hosts_maybe_in_op)
        summary = Text(op_name, style="cyan")
        if n_change:
            summary.append(f"  [{n_change} change]", style="green")
        if n_maybe:
            summary.append(f"  [{n_maybe} conditional]", style="yellow")
        if not n_change and not n_maybe:
            summary.append("  [no change]", style="dim")

        op_branch = parent.add(summary)
        for host_name in sorted(hosts_in_op):
            op_branch.add(routing.host_label(host_name, base_style="green"))
        for host_name in sorted(hosts_maybe_in_op):
            label = routing.host_label(host_name, base_style="yellow")
            label.append(" (conditional)", style="yellow")
            op_branch.add(label)

    console.print(tree)


def _result_summary(n_success: int, n_error: int, n_no_change: int) -> Text:
    parts = Text()
    if n_success:
        parts.append(f"  {n_success} ✓", style="green")
    if n_error:
        parts.append(f"  {n_error} ✗", style="red")
    if n_no_change:
        parts.append(f"  {n_no_change} –", style="blue")
    return parts


def print_results(state: State):
    tree = Tree(Text("Results", style="bold"), guide_style="dim")
    file_branches: dict[str, Any] = {}

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

        totals["hosts"] += hosts_in_op
        totals["success"] += len(hosts_in_op_success)
        totals["error"] += len(hosts_in_op_error)
        totals["no_change"] += len(hosts_in_op_no_change)

        filename, op_name = _split_op_name(pretty_op_name(state.op_meta[op_hash]))
        parent = tree
        if filename is not None:
            branch = file_branches.get(filename)
            if branch is None:
                branch = tree.add(Text(filename, style="bold magenta"))
                file_branches[filename] = branch
            parent = branch

        label = Text(op_name, style="red" if hosts_in_op_error else "cyan")
        label.append_text(
            _result_summary(
                len(hosts_in_op_success), len(hosts_in_op_error), len(hosts_in_op_no_change)
            )
        )
        op_branch = parent.add(label)
        for host_name in sorted(hosts_in_op_error):
            op_branch.add(routing.host_label(host_name, base_style="red", prefix="✗ "))

    grand = Text("Grand total", style="bold")
    grand.append_text(_result_summary(totals["success"], totals["error"], totals["no_change"]))
    tree.add(grand)

    console.print(tree)
