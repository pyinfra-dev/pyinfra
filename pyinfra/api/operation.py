"""
Operations are the core of pyinfra. The ``@operation`` wrapper intercepts calls
to the function and instead diff against the remote server, outputting commands
to the deploy state. This is then run later by pyinfra's ``__main__`` or the
:doc:`./pyinfra.api.operations` module.
"""

from __future__ import annotations

from functools import wraps
from io import StringIO
from types import FunctionType
from typing import Any, Iterator, Optional, Set, Tuple

import pyinfra
from pyinfra import context, logger
from pyinfra.context import ctx_host, ctx_state

from .arguments import AllArguments, get_execution_kwarg_keys, pop_global_arguments
from .command import PyinfraCommand, StringCommand
from .exceptions import OperationValueError, PyinfraError
from .host import Host
from .operations import run_host_op
from .state import State, StateOperationHostData, StateOperationMeta
from .util import (
    get_call_location,
    get_file_sha1,
    get_operation_order_from_stack,
    log_operation_start,
    make_hash,
)

op_meta_default = object()


class OperationMeta:
    combined_output_lines = None
    commands: Optional[list[Any]] = None
    changed: bool = False
    success: Optional[bool] = None

    def __init__(self, hash=None, is_change=False):
        self.hash = hash
        self.changed = is_change

    def __repr__(self) -> str:
        """
        Return Operation object as a string.
        """

        return f"OperationMeta(changed={self.changed}, hash={self.hash})"

    def set_combined_output_lines(self, combined_output_lines):
        self.combined_output_lines = combined_output_lines

    def set_commands(self, commands) -> None:
        self.commands = commands

    def set_result(self, success: bool) -> None:
        self.success = success

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


def add_op(state: State, op_func, *args, **kwargs):
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


def operation(
    pipeline_facts=None,
    is_idempotent: bool = True,
    idempotent_notice=None,
):
    """
    Decorator that takes a simple module function and turn it into the internal
    operation representation that consists of a list of commands + options
    (sudo, (sudo|su)_user, env).
    """

    def decorator(f):
        f.pipeline_facts = pipeline_facts
        f.is_idempotent = is_idempotent
        f.idempotent_notice = idempotent_notice
        return _wrap_operation(f)

    return decorator


def _wrap_operation(func):
    @wraps(func)
    def decorated_func(*args, **kwargs):
        state = context.state
        host = context.host

        # Configure operation
        #
        # Get the meta kwargs (globals that apply to all hosts)
        global_arguments, global_argument_keys = pop_global_arguments(kwargs)

        # If this op is being called inside another, just return here
        # (any unwanted/op-related kwargs removed above).
        if host.in_op and not host.in_callback_op:
            if global_argument_keys:
                _error_msg = "Nested operation called with global arguments: {0} ({1})".format(
                    global_argument_keys,
                    get_call_location(),
                )
                raise PyinfraError(_error_msg)
            return func(*args, **kwargs) or []

        names, add_args = _generate_operation_name(func, host, kwargs, global_arguments)
        op_order, op_hash = _solve_operation_consistency(names, state, host)

        # Ensure shared (between servers) operation meta, mutates state
        op_meta = _ensure_shared_op_meta(state, op_hash, op_order, global_arguments, names)

        # Attach normal args, if we're auto-naming this operation
        if add_args:
            op_meta = _attach_args(op_meta, args, kwargs)

        # Check if we're actually running the operation on this host
        # Run once and we've already added meta for this op? Stop here.
        if op_meta.global_arguments["_run_once"]:
            has_run = False
            for ops in state.ops.values():
                if op_hash in ops:
                    has_run = True
                    break

            if has_run:
                return OperationMeta(op_hash)

        # "Run" operation - here we make a generator that will yield out actual commands to execute
        # and, if we're diff-ing, we then iterate the generator now to determine if any changes
        # *would* be made based on the *current* remote state.

        def command_generator() -> Iterator[PyinfraCommand]:
            host.in_op = True
            # MY EYES, this is evil
            host.in_callback_op = (
                func.__name__ == "call" and func.__module__ == "pyinfra.operations.python"
            )
            host.current_op_hash = op_hash
            host.current_op_global_arguments = global_arguments

            try:
                for command in func(*args, **kwargs):
                    if isinstance(command, str):
                        command = StringCommand(command.strip())
                    yield command
            finally:
                host.in_op = False
                host.current_op_hash = None
                host.current_op_global_arguments = None

        op_is_change = False
        if state.should_check_for_changes():
            for command in command_generator():
                op_is_change = True
                break

        # Add host-specific operation data to state, this mutates state
        operation_meta = _add_host_op_to_state(
            state,
            host,
            op_hash,
            op_is_change,
            command_generator,
            global_arguments,
        )

        # If we're already in the execution phase, execute this operation immediately
        if state.is_executing:
            _execute_immediately(state, host, op_hash)

        # Return result meta for use in deploy scripts
        return operation_meta

    decorated_func._pyinfra_op = func  # type: ignore
    return decorated_func


def _generate_operation_name(func, host, kwargs, global_arguments):
    # Generate an operation name if needed (Module/Operation format)
    name = global_arguments.get("name")
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
def _ensure_shared_op_meta(
    state: State,
    op_hash: str,
    op_order: Tuple[int],
    global_arguments: AllArguments,
    names: Set[str],
):
    op_meta = state.op_meta.setdefault(op_hash, StateOperationMeta(op_order))

    for key in get_execution_kwarg_keys():
        global_value = global_arguments.pop(key)  # type: ignore[misc]
        op_meta_value = op_meta.global_arguments.get(key, op_meta_default)

        if op_meta_value is not op_meta_default and global_value != op_meta_value:
            raise OperationValueError("Cannot have different values for `{0}`.".format(key))

        op_meta.global_arguments[key] = global_value  # type: ignore[literal-required]

    # Add any new names to the set
    op_meta.names.update(names)

    return op_meta


def _execute_immediately(state, host, op_hash):
    logger.warning(
        f"Note: nested operations are currently in beta ({get_call_location()})\n"
        "    More information: "
        "https://docs.pyinfra.com/en/2.x/using-operations.html#nested-operations",
    )
    op_meta = state.get_op_meta(op_hash)
    op_data = state.get_op_data_for_host(host, op_hash)
    op_data.parent_op_hash = host.executing_op_hash
    log_operation_start(op_meta, op_types=["nested"], prefix="")
    run_host_op(state, host, op_hash)


def _get_arg_value(arg):
    if isinstance(arg, FunctionType):
        return arg.__name__
    if isinstance(arg, StringIO):
        return f"StringIO(hash={get_file_sha1(arg)})"
    return arg


def _attach_args(op_meta, args, kwargs):
    for arg in args:
        if arg not in op_meta.args:
            op_meta.args.append(str(_get_arg_value(arg)))

    # Attach keyword args
    for key, value in kwargs.items():
        arg = "=".join((str(key), str(_get_arg_value(value))))
        if arg not in op_meta.args:
            op_meta.args.append(arg)

    return op_meta


# NOTE: this function mutates state.meta for this host
def _add_host_op_to_state(
    state: State,
    host: Host,
    op_hash: str,
    is_change: bool,
    command_generator,
    global_arguments,
) -> OperationMeta:
    host_meta = state.get_meta_for_host(host)

    host_meta.ops += 1

    if is_change:
        host_meta.ops_change += 1
    else:
        host_meta.ops_no_change += 1

    operation_meta = OperationMeta(op_hash, is_change)

    # Add the server-relevant commands
    op_data = StateOperationHostData(command_generator, global_arguments, operation_meta)
    state.set_op_data_for_host(host, op_hash, op_data)

    return operation_meta
