from __future__ import annotations

import traceback
from itertools import product
from socket import error as socket_error, timeout as timeout_error
from typing import TYPE_CHECKING, Optional, cast

import click
import gevent
from paramiko import SSHException

from pyinfra import logger
from pyinfra.connectors.util import CommandOutput, OutputLine
from pyinfra.context import ctx_host, ctx_state
from pyinfra.progress import progress_spinner

from .arguments import ConnectorArguments, get_connector_argument_keys
from .command import FunctionCommand, PyinfraCommand, StringCommand
from .exceptions import PyinfraError
from .util import (
    format_exception,
    log_error_or_warning,
    log_host_command_error,
    log_operation_start,
    memoize,
    print_host_combined_output,
)

if TYPE_CHECKING:
    from .inventory import Host
    from .state import State


@memoize
def show_pre_or_post_condition_warning(condition_name):
    logger.warning("The `{0}` argument is in beta!".format(condition_name))


def _run_shell_command(
    state: "State",
    host: "Host",
    command: StringCommand,
    connector_arguments: ConnectorArguments,
    timeout: int,
) -> tuple[bool, CommandOutput]:
    status = False
    combined_output_lines = CommandOutput([])

    try:
        status, combined_output_lines = command.execute(state, host, connector_arguments)
    except (timeout_error, socket_error, SSHException) as e:
        log_host_command_error(host, e, timeout=timeout)

    # If we failed and have no already printed the stderr, print it
    if status is False and not state.print_output:
        print_host_combined_output(host, combined_output_lines)

    return status, combined_output_lines


# Run a single host operation
#


def run_host_op(state: "State", host: "Host", op_hash: str) -> Optional[bool]:
    state.trigger_callbacks("operation_host_start", host, op_hash)

    if op_hash not in state.ops[host]:
        logger.info("{0}{1}".format(host.print_prefix, click.style("Skipped", "blue")))
        return True

    op_meta = state.get_op_meta(op_hash)
    logger.debug("Starting operation %r on %s", op_meta.names, host)

    if host.executing_op_hash is None:
        host.executing_op_hash = op_hash
    else:
        host.nested_executing_op_hash = op_hash

    try:
        return _run_host_op(state, host, op_hash)
    finally:
        if host.nested_executing_op_hash:
            host.nested_executing_op_hash = None
        else:
            host.executing_op_hash = None


def _run_host_op(state: "State", host: "Host", op_hash: str) -> Optional[bool]:
    op_data = state.get_op_data_for_host(host, op_hash)
    global_arguments = op_data.global_arguments

    ignore_errors = global_arguments["_ignore_errors"]
    continue_on_error = global_arguments["_continue_on_error"]
    timeout = global_arguments["_timeout"]

    command_generator = op_data.command_generator()

    executor_kwarg_keys = get_connector_argument_keys()
    base_connector_arguments: ConnectorArguments = (
        cast(  # https://github.com/python/mypy/issues/10371
            ConnectorArguments,
            {key: global_arguments[key] for key in executor_kwarg_keys if key in global_arguments},
        )
    )

    did_error = False
    executed_commands = 0
    commands = []
    all_combined_output_lines: list[OutputLine] = []

    for command in command_generator:
        commands.append(command)

        status = False

        connector_arguments = base_connector_arguments.copy()
        connector_arguments.update(command.connector_arguments)

        if not isinstance(command, PyinfraCommand):
            raise TypeError("{0} is an invalid pyinfra command!".format(command))

        if isinstance(command, FunctionCommand):
            try:
                status = command.execute(state, host, connector_arguments)
            except Exception as e:  # Custom functions could do anything, so expect anything!
                _formatted_exc = format_exception(e)
                _error_msg = "Unexpected error in Python callback: {0}".format(_formatted_exc)
                _error_msg_styled = click.style(_error_msg, "red")
                _error_log = "{0}{1}".format(host.print_prefix, _error_msg_styled)
                logger.warning(traceback.format_exc())
                logger.error(_error_log)

        elif isinstance(command, StringCommand):
            status, combined_output_lines = _run_shell_command(
                state, host, command, connector_arguments, timeout
            )
            all_combined_output_lines.extend(combined_output_lines)

        else:
            try:
                status = command.execute(state, host, connector_arguments)
            except (timeout_error, socket_error, SSHException, IOError) as e:
                log_host_command_error(host, e, timeout=timeout)

        # Break the loop to trigger a failure
        if status is False:
            did_error = True
            if continue_on_error is True:
                continue
            break

        executed_commands += 1

    # Handle results
    #

    return_status = not did_error
    host_results = state.get_results_for_host(host)

    if did_error is False:
        host_results.ops += 1
        host_results.success_ops += 1

        _status_log = "Success" if executed_commands > 0 else "No changes"
        _click_log_status = click.style(_status_log, "green")
        logger.info("{0}{1}".format(host.print_prefix, _click_log_status))

        if global_arguments["_on_success"]:
            global_arguments["_on_success"](state, host, op_hash)

        state.trigger_callbacks("operation_host_success", host, op_hash)
    else:
        if ignore_errors:
            host_results.ignored_error_ops += 1
        else:
            host_results.error_ops += 1

        if executed_commands:
            host_results.partial_ops += 1

        _command_description = f"executed {executed_commands} commands"
        log_error_or_warning(host, ignore_errors, _command_description, continue_on_error)

        if global_arguments["_on_error"]:
            global_arguments["_on_error"](state, host, op_hash)

        # Ignored, op "completes" w/ ignored error
        if ignore_errors:
            host_results.ops += 1
            return_status = True

        # Unignored error -> False
        state.trigger_callbacks("operation_host_error", host, op_hash)

    # Only set result if we actually did something (failed or executed >0 commands)
    if return_status is False or (return_status is True and executed_commands > 0):
        op_data.operation_meta.set_result(return_status)

    op_data.operation_meta.set_commands(commands)
    op_data.operation_meta.set_combined_output_lines(all_combined_output_lines)

    return return_status


# Run all operations strategies
#


def _run_host_op_with_context(state: "State", host: "Host", op_hash: str):
    with ctx_host.use(host):
        return run_host_op(state, host, op_hash)


def _run_host_ops(state: "State", host: "Host", progress=None):
    """
    Run all ops for a single server.
    """

    logger.debug("Running all ops on %s", host)

    for op_hash in state.get_op_order():
        op_meta = state.get_op_meta(op_hash)
        log_operation_start(op_meta)

        result = _run_host_op_with_context(state, host, op_hash)

        # Trigger CLI progress if provided
        if progress:
            progress((host, op_hash))

        if result is False:
            raise PyinfraError(
                "Error in operation {0} on {1}".format(
                    ", ".join(op_meta.names),
                    host,
                ),
            )


def _run_serial_ops(state: "State"):
    """
    Run all ops for all servers, one server at a time.
    """

    for host in list(state.inventory.iter_active_hosts()):
        host_operations = product([host], state.get_op_order())
        with progress_spinner(host_operations) as progress:
            try:
                _run_host_ops(
                    state,
                    host,
                    progress=progress,
                )
            except PyinfraError:
                state.fail_hosts({host})


def _run_no_wait_ops(state: "State"):
    """
    Run all ops for all servers at once.
    """

    hosts_operations = product(state.inventory.iter_active_hosts(), state.get_op_order())
    with progress_spinner(hosts_operations) as progress:
        # Spawn greenlet for each host to run *all* ops
        if state.pool is None:
            raise PyinfraError("No pool found on state.")
        greenlets = [
            state.pool.spawn(
                _run_host_ops,
                state,
                host,
                progress=progress,
            )
            for host in state.inventory.iter_active_hosts()
        ]
        gevent.joinall(greenlets)


def _run_single_op(state: "State", op_hash: str):
    """
    Run a single operation for all servers. Can be configured to run in serial.
    """

    state.trigger_callbacks("operation_start", op_hash)

    op_meta = state.get_op_meta(op_hash)
    log_operation_start(op_meta)

    failed_hosts = set()

    if op_meta.global_arguments["_serial"]:
        with progress_spinner(state.inventory.iter_active_hosts()) as progress:
            # For each host, run the op
            for host in state.inventory.iter_active_hosts():
                result = _run_host_op_with_context(state, host, op_hash)
                progress(host)

                if not result:
                    failed_hosts.add(host)

    else:
        # Start with the whole inventory in one batch
        batches = [list(state.inventory.iter_active_hosts())]

        # If parallel set break up the inventory into a series of batches
        if op_meta.global_arguments["_parallel"]:
            parallel = op_meta.global_arguments["_parallel"]
            hosts = list(state.inventory.iter_active_hosts())

            batches = [hosts[i : i + parallel] for i in range(0, len(hosts), parallel)]

        for batch in batches:
            with progress_spinner(batch) as progress:
                # Spawn greenlet for each host
                if state.pool is None:
                    raise PyinfraError("No pool found on state.")
                greenlet_to_host = {
                    state.pool.spawn(_run_host_op_with_context, state, host, op_hash): host
                    for host in batch
                }

                # Trigger CLI progress as hosts complete if provided
                for greenlet in gevent.iwait(greenlet_to_host.keys()):
                    host = greenlet_to_host[greenlet]
                    progress(host)

                # Get all the results
                for greenlet, host in greenlet_to_host.items():
                    if not greenlet.get():
                        failed_hosts.add(host)

    # Now all the batches/hosts are complete, fail any failures
    state.fail_hosts(failed_hosts)

    state.trigger_callbacks("operation_end", op_hash)


def run_ops(state: "State", serial: bool = False, no_wait: bool = False):
    """
    Runs all operations across all servers in a configurable manner.

    Args:
        state (``pyinfra.api.State`` obj): the deploy state to execute
        serial (boolean): whether to run operations host by host
        no_wait (boolean): whether to wait for all hosts between operations
    """

    # Flag state as deploy in process
    state.is_executing = True

    with ctx_state.use(state):
        # Run all ops, but server by server
        if serial:
            _run_serial_ops(state)
        # Run all the ops on each server in parallel (not waiting at each operation)
        elif no_wait:
            _run_no_wait_ops(state)
        # Default: run all ops in order, waiting at each for all servers to complete
        else:
            for op_hash in state.get_op_order():
                _run_single_op(state, op_hash)
