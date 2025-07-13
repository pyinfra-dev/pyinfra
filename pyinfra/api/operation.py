"""
Operations are the core of pyinfra. The ``@operation`` wrapper intercepts calls
to the function and instead diff against the remote server, outputting commands
to the deploy state. This is then run later by pyinfra's ``__main__`` or the
:doc:`./pyinfra.api.operations` module.
"""

from __future__ import annotations

from functools import wraps
from inspect import signature
from io import StringIO
from types import FunctionType
from typing import TYPE_CHECKING, Any, Callable, Generator, Iterator, Optional, cast

from typing_extensions import ParamSpec, override

import pyinfra
from pyinfra import context, logger
from pyinfra.context import ctx_host, ctx_state

from .arguments import EXECUTION_KWARG_KEYS, AllArguments, pop_global_arguments
from .arguments_typed import PyinfraOperation
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

if TYPE_CHECKING:
    from pyinfra.connectors.util import CommandOutput


class OperationMeta:
    _hash: str

    _combined_output: Optional["CommandOutput"] = None
    _commands: Optional[list[Any]] = None
    _maybe_is_change: Optional[bool] = None
    _success: Optional[bool] = None

    def __init__(self, hash, is_change: Optional[bool]):
        self._hash = hash
        self._maybe_is_change = is_change

    @override
    def __repr__(self) -> str:
        """
        Return Operation object as a string.
        """

        if self._commands is not None:
            return (
                "OperationMeta(executed=True, "
                f"success={self.did_succeed()}, hash={self._hash}, commands={len(self._commands)})"
            )
        return (
            "OperationMeta(executed=False, "
            f"maybeChange={self._maybe_is_change}, hash={self._hash})"
        )

    # Completion & status checks
    def set_complete(
        self,
        success: bool,
        commands: list[Any],
        combined_output: "CommandOutput",
    ) -> None:
        if self.is_complete():
            raise RuntimeError("Cannot complete an already complete operation")
        self._success = success
        self._commands = commands
        self._combined_output = combined_output

    def is_complete(self) -> bool:
        return self._success is not None

    def _raise_if_not_complete(self) -> None:
        if not self.is_complete():
            raise RuntimeError("Cannot evaluate operation result before execution")

    @property
    def executed(self) -> bool:
        if self._commands is None:
            return False
        return len(self._commands) > 0

    @property
    def will_change(self) -> bool:
        if self._maybe_is_change is not None:
            return self._maybe_is_change

        op_data = context.state.get_op_data_for_host(context.host, self._hash)
        cmd_gen = op_data.command_generator
        for _ in cmd_gen():
            self._maybe_is_change = True
            return True
        self._maybe_is_change = False
        return False

    def did_change(self) -> bool:
        self._raise_if_not_complete()
        return bool(self._success and len(self._commands or []) > 0)

    def did_not_change(self) -> bool:
        return not self.did_change()

    def did_succeed(self, _raise_if_not_complete=True) -> bool:
        if _raise_if_not_complete:
            self._raise_if_not_complete()
        return self._success is True

    def did_error(self) -> bool:
        self._raise_if_not_complete()
        return self._success is False

    # TODO: deprecated, remove in v4
    @property
    def changed(self) -> bool:
        if self.is_complete():
            return self.did_change()
        return self.will_change

    @property
    def stdout_lines(self) -> list[str]:
        self._raise_if_not_complete()
        assert self._combined_output is not None
        return self._combined_output.stdout_lines

    @property
    def stderr_lines(self) -> list[str]:
        self._raise_if_not_complete()
        assert self._combined_output is not None
        return self._combined_output.stderr_lines

    @property
    def stdout(self) -> str:
        return "\n".join(self.stdout_lines)

    @property
    def stderr(self) -> str:
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


P = ParamSpec("P")


def operation(
    is_idempotent: bool = True,
    idempotent_notice: Optional[str] = None,
    is_deprecated: bool = False,
    deprecated_for: Optional[str] = None,
    _set_in_op: bool = True,
) -> Callable[[Callable[P, Generator]], PyinfraOperation[P]]:
    """
    Decorator that takes a simple module function and turn it into the internal
    operation representation that consists of a list of commands + options
    (sudo, (sudo|su)_user, env).
    """

    def decorator(f: Callable[P, Generator]) -> PyinfraOperation[P]:
        f.is_idempotent = is_idempotent  # type: ignore[attr-defined]
        f.idempotent_notice = idempotent_notice  # type: ignore[attr-defined]
        f.is_deprecated = is_deprecated  # type: ignore[attr-defined]
        f.deprecated_for = deprecated_for  # type: ignore[attr-defined]
        return _wrap_operation(f, _set_in_op=_set_in_op)

    return decorator


def _wrap_operation(func: Callable[P, Generator], _set_in_op: bool = True) -> PyinfraOperation[P]:
    @wraps(func)
    def decorated_func(*args: P.args, **kwargs: P.kwargs) -> OperationMeta:
        state = context.state
        host = context.host

        if host.in_op:
            raise Exception(
                "Operation called within another operation, this is not allowed! Use the `_inner` "
                + "function to call the underlying operation."
            )

        if func.is_deprecated:  # type: ignore[attr-defined]
            if func.deprecated_for:  # type: ignore[attr-defined]
                logger.warning(
                    f"The {get_operation_name_from_func(func)} operation is "
                    + f"deprecated, please use: {func.deprecated_for}",  # type: ignore[attr-defined] # noqa
                )
            else:
                logger.warning(f"The {get_operation_name_from_func(func)} operation is deprecated")

        # Configure operation
        #
        # Get the meta kwargs (globals that apply to all hosts)
        global_arguments, global_argument_keys = pop_global_arguments(state, host, kwargs)

        names, add_args = generate_operation_name(func, host, kwargs, global_arguments)
        op_order, op_hash = solve_operation_consistency(names, state, host)

        # Ensure shared (between servers) operation meta, mutates state
        op_meta = ensure_shared_op_meta(state, op_hash, op_order, global_arguments, names)

        # Attach normal args, if we're auto-naming this operation
        if add_args:
            op_meta = attach_args(op_meta, args, kwargs)

        # Check if we're actually running the operation on this host
        # Run once and we've already added meta for this op? Stop here.
        if op_meta.global_arguments["_run_once"]:
            has_run = False
            for ops in state.ops.values():
                if op_hash in ops:
                    has_run = True
                    break

            if has_run:
                return OperationMeta(op_hash, is_change=False)

        # Grab a reference to any *current* deploy data as this may change when
        # we later evaluate the operation at runtime.This means we put back the
        # expected deploy data.
        current_deploy_data = host.current_deploy_data

        # "Run" operation - here we make a generator that will yield out actual commands to execute
        # and, if we're diff-ing, we then iterate the generator now to determine if any changes
        # *would* be made based on the *current* remote state.

        def command_generator() -> Iterator[PyinfraCommand]:
            # Check global _if argument function and do nothing if returns False
            if state.is_executing:
                _ifs = global_arguments.get("_if")
                if isinstance(_ifs, list) and not all(_if() for _if in _ifs):
                    return
                elif callable(_ifs) and not _ifs():
                    return

            host.in_op = _set_in_op
            host.current_op_hash = op_hash
            host.current_op_global_arguments = global_arguments
            host.current_op_deploy_data = current_deploy_data

            try:
                for command in func(*args, **kwargs):
                    if isinstance(command, str):
                        command = StringCommand(command.strip())
                    yield command
            finally:
                host.in_op = False
                host.current_op_hash = None
                host.current_op_global_arguments = None
                host.current_op_deploy_data = None

        op_is_change = None
        if state.should_check_for_changes():
            op_is_change = False
            for _ in command_generator():
                op_is_change = True
                break
        else:
            # If not calling the op function to check for change we still want to ensure the args
            # are valid, so use Signature.bind to trigger any TypeError.
            signature(func).bind(*args, **kwargs)

        # Add host-specific operation data to state, this mutates state
        host_meta = state.get_meta_for_host(host)
        host_meta.ops += 1
        if op_is_change:
            host_meta.ops_change += 1
        else:
            host_meta.ops_no_change += 1

        operation_meta = OperationMeta(op_hash, op_is_change)

        # Add the server-relevant commands
        op_data = StateOperationHostData(command_generator, global_arguments, operation_meta)
        state.set_op_data_for_host(host, op_hash, op_data)

        # If we're already in the execution phase, execute this operation immediately
        if state.is_executing:
            execute_immediately(state, host, op_hash)

        # Return result meta for use in deploy scripts
        return operation_meta

    decorated_func._inner = func  # type: ignore[attr-defined]
    return cast(PyinfraOperation[P], decorated_func)


def get_operation_name_from_func(func):
    if func.__module__:
        module_bits = func.__module__.split(".")
        module_name = module_bits[-1]
        return "{0}.{1}".format(module_name, func.__name__)
    else:
        return func.__name__


def generate_operation_name(func, host, kwargs, global_arguments):
    # Generate an operation name if needed (Module/Operation format)
    name = global_arguments.get("name")
    add_args = False
    if name:
        names = {name}
    else:
        add_args = True
        name = get_operation_name_from_func(func)
        names = {name}

    if host.current_deploy_name:
        names = {"{0} | {1}".format(host.current_deploy_name, name) for name in names}

    return names, add_args


def solve_operation_consistency(names, state, host):
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
def ensure_shared_op_meta(
    state: State,
    op_hash: str,
    op_order: tuple[int, ...],
    global_arguments: AllArguments,
    names: set[str],
):
    op_meta = state.op_meta.setdefault(op_hash, StateOperationMeta(op_order))

    for key in EXECUTION_KWARG_KEYS:
        global_value = global_arguments.pop(key)  # type: ignore[misc]
        op_meta_value = op_meta.global_arguments.get(key, op_meta_default)

        if op_meta_value is not op_meta_default and global_value != op_meta_value:
            raise OperationValueError("Cannot have different values for `{0}`.".format(key))

        op_meta.global_arguments[key] = global_value  # type: ignore[literal-required]

    # Add any new names to the set
    op_meta.names.update(names)

    return op_meta


def execute_immediately(state, host, op_hash):
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


def attach_args(op_meta, args, kwargs):
    for arg in args:
        if arg not in op_meta.args:
            op_meta.args.append(str(_get_arg_value(arg)))

    # Attach keyword args
    for key, value in kwargs.items():
        arg = "=".join((str(key), str(_get_arg_value(value))))
        if arg not in op_meta.args:
            op_meta.args.append(arg)

    return op_meta
