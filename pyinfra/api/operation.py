"""
Operations are the core of pyinfra. The ``@operation`` wrapper intercepts calls
to the function and instead diff against the remote server, outputting commands
to the deploy state. This is then run later by pyinfra's ``__main__`` or the
:doc:`./pyinfra.api.operations` module.
"""

from functools import wraps
from types import FunctionType
from typing import TYPE_CHECKING

import pyinfra
from pyinfra import context, logger
from pyinfra.context import ctx_host, ctx_state

from .arguments import get_execution_kwarg_keys, pop_global_arguments
from .command import StringCommand
from .exceptions import OperationValueError, PyinfraError
from .host import Host
from .operations import run_host_op
from .util import (
    get_args_kwargs_spec,
    get_call_location,
    get_operation_order_from_stack,
    log_operation_start,
    make_hash,
    memoize,
)

if TYPE_CHECKING:
    from pyinfra.api.state import State

op_meta_default = object()


class OperationMeta:
    combined_output_lines = None

    def __init__(self, hash=None, commands=None):
        # Wrap all the attributes
        commands = commands or []
        self.commands = commands
        self.hash = hash

        # Changed flag = did we do anything?
        self.changed = len(self.commands) > 0

    def __repr__(self):
        """
        Return Operation object as a string.
        """

        return (
            f"OperationMeta(commands={len(self.commands)}, "
            f"changed={self.changed}, hash={self.hash})"
        )

    def set_combined_output_lines(self, combined_output_lines):
        self.combined_output_lines = combined_output_lines

    def _get_lines(self, types=("stdout", "stderr")):
        if self.combined_output_lines is None:
            raise AttributeError("Output is not available until operations have been executed")

        return [line for type_, line in self.combined_output_lines if type_ in types]

    @property
    def stdout_lines(self):
        return self._get_lines(types=("stdout",))

    @property
    def stderr_lines(self):
        return self._get_lines(types=("stderr",))

    @property
    def stdout(self):
        return "\n".join(self.stdout_lines)

    @property
    def stderr(self):
        return "\n".join(self.stderr_lines)


def add_op(state: "State", op_func, *args, **kwargs):
    """
    Prepare & add an operation to ``pyinfra.state`` by executing it on all hosts.

    Args:
        state (``pyinfra.api.State`` obj): the deploy state to add the operation
        to op_func (function): the operation function from one of the modules,
        ie ``server.user``
        args/kwargs: passed to the operation function
    """

    if pyinfra.is_cli:
        raise PyinfraError(
            ("`add_op` should not be called when pyinfra is executing in CLI mode! ({0})").format(
                get_call_location(),
            ),
        )

    hosts = kwargs.pop("host", state.inventory.iter_active_hosts())
    if isinstance(hosts, Host):
        hosts = [hosts]

    with ctx_state.use(state):
        results = {}
        for op_host in hosts:
            with ctx_host.use(op_host):
                results[op_host] = op_func(*args, **kwargs)

    return results


@memoize
def show_state_host_arguments_warning(call_location):
    logger.warning(
        (
            "{0}:\n\tLegacy operation function detected! Operations should no longer define "
            "`state` and `host` arguments."
        ).format(call_location),
    )


def operation(
    func=None,
    pipeline_facts=None,
    is_idempotent: bool = True,
    idempotent_notice=None,
    frame_offset: int = 1,
):
    """
    Decorator that takes a simple module function and turn it into the internal
    operation representation that consists of a list of commands + options
    (sudo, (sudo|su)_user, env).
    """

    # If not decorating, return function with config attached
    if func is None:

        def decorator(f):
            f.pipeline_facts = pipeline_facts
            f.is_idempotent = is_idempotent
            f.idempotent_notice = idempotent_notice
            return operation(f, frame_offset=2)

        return decorator

    # Check whether an operation is "legacy" - ie contains state=None, host=None kwargs
    # TODO: remove this in v3
    is_legacy = False
    args, kwargs = get_args_kwargs_spec(func)
    if all(key in kwargs and kwargs[key] is None for key in ("state", "host")):
        show_state_host_arguments_warning(get_call_location(frame_offset=frame_offset))
        is_legacy = True
    func.is_legacy = is_legacy

    # Actually decorate!
    @wraps(func)
    def decorated_func(*args, **kwargs):
        state = context.state
        host = context.host

        # Configure operation
        #
        # Get the meta kwargs (globals that apply to all hosts)
        global_kwargs, global_kwarg_keys = pop_global_arguments(kwargs)

        # If this op is being called inside another, just return here
        # (any unwanted/op-related kwargs removed above).
        if host.in_op:
            if global_kwarg_keys:
                _error_msg = "Nested operation called with global arguments: {0} ({1})".format(
                    global_kwarg_keys,
                    get_call_location(),
                )
                raise PyinfraError(_error_msg)
            return func(*args, **kwargs) or []

        kwargs = _solve_legacy_operation_arguments(func, state, host, kwargs)
        names, add_args = _generate_operation_name(func, host, kwargs, global_kwargs)
        op_order, op_hash = _solve_operation_consistency(names, state, host)

        # Ensure shared (between servers) operation meta, mutates state
        op_meta = _ensure_shared_op_meta(state, op_hash, op_order, global_kwargs, names)

        # Attach normal args, if we're auto-naming this operation
        if add_args:
            op_meta = _attach_args(op_meta, args, kwargs)

        # Check if we're actually running the operation on this host
        # Run once and we've already added meta for this op? Stop here.
        if op_meta["run_once"]:
            has_run = False
            for ops in state.ops.values():
                if op_hash in ops:
                    has_run = True
                    break

            if has_run:
                return OperationMeta(op_hash)

        # "Run" operation
        #

        # Otherwise, flag as in-op and run it to get the commands
        host.in_op = True
        host.current_op_hash = op_hash
        host.current_op_global_kwargs = global_kwargs

        # Convert to list as the result may be a generator
        commands = func(*args, **kwargs)
        commands = [  # convert any strings -> StringCommand's
            StringCommand(command.strip()) if isinstance(command, str) else command
            for command in commands
        ]

        host.in_op = False
        host.current_op_hash = None
        host.current_op_global_kwargs = None

        # Add host-specific operation data to state, this mutates state
        operation_meta = _update_state_meta(state, host, commands, op_hash, op_meta, global_kwargs)

        # Return result meta for use in deploy scripts
        return operation_meta

    decorated_func._pyinfra_op = func  # type: ignore
    return decorated_func


def _solve_legacy_operation_arguments(op_func, state, host, kwargs):
    """
    Solve legacy operation arguments.
    """

    # If this is a legacy operation function (ie - state & host arg kwargs), ensure that state
    # and host are included as kwargs.

    # Legacy operation arguments
    if op_func.is_legacy:
        if "state" not in kwargs:
            kwargs["state"] = state
        if "host" not in kwargs:
            kwargs["host"] = host
    # If not legacy, pop off any state/host kwargs that may come from legacy @deploy functions
    else:
        kwargs.pop("state", None)
        kwargs.pop("host", None)

    return kwargs


def _generate_operation_name(func, host, kwargs, global_kwargs):
    # Generate an operation name if needed (Module/Operation format)
    name = global_kwargs.get("name")
    add_args = False
    if name:
        names = {name}
    else:
        add_args = True

        if func.__module__:
            module_bits = func.__module__.split(".")
            module_name = module_bits[-1]
            name = "{0}/{1}".format(module_name.title(), func.__name__.title())
        else:
            name = func.__name__

        names = {name}

    if host.current_deploy_name:
        names = {"{0} | {1}".format(host.current_deploy_name, name) for name in names}

    return names, add_args


def _solve_operation_consistency(names, state, host):
    # Operation order is used to tie-break available nodes in the operation DAG, in CLI mode
    # we use stack call order so this matches as defined by the user deploy code.
    if pyinfra.is_cli:
        op_order = get_operation_order_from_stack(state)
    # In API mode we just increase the order for each host
    else:
        op_order = [len(host.op_hash_order)]

    if host.loop_position:
        op_order.extend(host.loop_position)

    # Make a hash from the call stack lines
    op_hash = make_hash(op_order)

    # Avoid adding duplicates! This happens if an operation is called within
    # a loop - such that the filename/lineno/code _are_ the same, but the
    # arguments might be different. We just append an increasing number to
    # the op hash and also handle below with the op order.
    duplicate_op_count = 0
    while op_hash in host.op_hash_order:
        logger.debug("Duplicate hash ({0}) detected!".format(op_hash))
        op_hash = "{0}-{1}".format(op_hash, duplicate_op_count)
        duplicate_op_count += 1

    host.op_hash_order.append(op_hash)
    if duplicate_op_count:
        op_order.append(duplicate_op_count)

    op_order = tuple(op_order)
    logger.debug(f"Adding operation, {names}, opOrder={op_order}, opHash={op_hash}")
    return op_order, op_hash


# NOTE: this function mutates state.op_meta for this hash
def _ensure_shared_op_meta(state, op_hash, op_order, global_kwargs, names):
    op_meta = state.op_meta.setdefault(
        op_hash,
        {
            "names": set(),
            "args": [],
            "op_order": op_order,
        },
    )

    for key in get_execution_kwarg_keys():
        global_value = global_kwargs.pop(key)
        op_meta_value = op_meta.get(key, op_meta_default)

        if op_meta_value is not op_meta_default and global_value != op_meta_value:
            raise OperationValueError("Cannot have different values for `{0}`.".format(key))

        op_meta[key] = global_value

    # Add any new names to the set
    op_meta["names"].update(names)

    return op_meta


def _execute_immediately(state, host, op_data, op_meta, op_hash):
    logger.warning(
        f"Note: nested operations are currently in beta ({get_call_location()})\n"
        "    More information: "
        "https://docs.pyinfra.com/en/2.x/using-operations.html#nested-operations",
    )
    op_data["parent_op_hash"] = host.executing_op_hash
    log_operation_start(op_meta, op_types=["nested"], prefix="")
    run_host_op(state, host, op_hash)


def _attach_args(op_meta, args, kwargs):
    for arg in args:
        if isinstance(arg, FunctionType):
            arg = arg.__name__

        if arg not in op_meta["args"]:
            op_meta["args"].append(arg)

    # Attach keyword args
    for key, value in kwargs.items():
        if isinstance(value, FunctionType):
            value = value.__name__

        arg = "=".join((str(key), str(value)))
        if arg not in op_meta["args"]:
            op_meta["args"].append(arg)

    return op_meta


# NOTE: this function mutates state.meta for this host
def _update_state_meta(state, host, commands, op_hash, op_meta, global_kwargs):
    # We're doing some commands, meta/ops++
    state.meta[host]["ops"] += 1
    state.meta[host]["commands"] += len(commands)

    if commands:
        state.meta[host]["ops_change"] += 1
    else:
        state.meta[host]["ops_no_change"] += 1

    operation_meta = OperationMeta(op_hash, commands)

    # Add the server-relevant commands
    op_data = {
        "commands": commands,
        "global_kwargs": global_kwargs,
        "operation_meta": operation_meta,
    }
    state.set_op_data(host, op_hash, op_data)

    # If we're already in the execution phase, execute this operation immediately
    if state.is_executing:
        _execute_immediately(state, host, op_data, op_meta, op_hash)

    return operation_meta
