from __future__ import print_function, unicode_literals

import traceback

from itertools import product
from socket import (
    error as socket_error,
    timeout as timeout_error,
)

import click
import gevent
import six

from paramiko import SSHException

import pyinfra

from pyinfra import logger
from pyinfra.progress import progress_spinner

from .command import (
    FunctionCommand,
    PyinfraCommand,
    StringCommand,
)
from .exceptions import PyinfraError
from .operation_kwargs import get_executor_kwarg_keys
from .util import (
    format_exception,
    log_error_or_warning,
    log_host_command_error,
    memoize,
    print_host_combined_output,
)


@memoize
def show_pre_or_post_condition_warning(condition_name):
    logger.warning('The `{0}` argument is in beta!'.format(condition_name))


def _run_shell_command(state, host, command, global_kwargs, executor_kwargs):
    status = False
    combined_output_lines = []

    try:
        status, combined_output_lines = command.execute(state, host, executor_kwargs)
    except (timeout_error, socket_error, SSHException) as e:
        log_host_command_error(
            host,
            e,
            timeout=global_kwargs['timeout'],
        )

    # If we failed and have no already printed the stderr, print it
    if status is False and not state.print_output:
        print_host_combined_output(host, combined_output_lines)

    return status


def _run_server_op(state, host, op_hash):
    state.trigger_callbacks('operation_host_start', host, op_hash)

    if op_hash not in state.ops[host]:
        logger.info('{0}{1}'.format(host.print_prefix, click.style('Skipped', 'blue')))
        return True

    op_data = state.get_op_data(host, op_hash)
    global_kwargs = op_data['global_kwargs']

    op_meta = state.get_op_meta(op_hash)

    ignore_errors = global_kwargs['ignore_errors']

    logger.debug('Starting operation {0} on {1}'.format(
        ', '.join(op_meta['names']), host,
    ))

    executor_kwarg_keys = get_executor_kwarg_keys()
    base_executor_kwargs = {
        key: global_kwargs[key]
        for key in executor_kwarg_keys
        if key in global_kwargs
    }

    precondition = global_kwargs['precondition']
    if precondition:
        show_pre_or_post_condition_warning('precondition')
    if precondition and not _run_shell_command(
        state, host, StringCommand(precondition), global_kwargs, base_executor_kwargs,
    ):
        log_error_or_warning(
            host, ignore_errors,
            description='precondition failed: {0}'.format(precondition),
        )
        if not ignore_errors:
            state.trigger_callbacks('operation_host_error', host, op_hash)
            return False

    state.ops_run.add(op_hash)

    # ...loop through each command
    for i, command in enumerate(op_data['commands']):

        status = False

        executor_kwargs = base_executor_kwargs.copy()
        executor_kwargs.update(command.executor_kwargs)

        # Now we attempt to execute the command
        #

        if not isinstance(command, PyinfraCommand):
            raise TypeError('{0} is an invalid pyinfra command!'.format(command))

        if isinstance(command, FunctionCommand):
            try:
                status = command.execute(state, host, executor_kwargs)
            except Exception as e:  # Custom functions could do anything, so expect anything!
                logger.warning(traceback.format_exc())
                logger.error('{0}{1}'.format(
                    host.print_prefix,
                    click.style(
                        'Unexpected error in Python callback: {0}'.format(
                            format_exception(e),
                        ),
                        'red',
                    ),
                ))

        elif isinstance(command, StringCommand):
            status = _run_shell_command(state, host, command, global_kwargs, executor_kwargs)

        else:
            try:
                status = command.execute(state, host, executor_kwargs)
            except (timeout_error, socket_error, SSHException, IOError) as e:
                log_host_command_error(
                    host,
                    e,
                    timeout=global_kwargs['timeout'],
                )

        # Break the loop to trigger a failure
        if status is False:
            break

        state.results[host]['commands'] += 1

    # Commands didn't break, so count our successes & return True!
    else:
        postcondition = global_kwargs['postcondition']
        if postcondition:
            show_pre_or_post_condition_warning('postcondition')
        if postcondition and not _run_shell_command(
            state, host, StringCommand(postcondition), global_kwargs, base_executor_kwargs,
        ):
            log_error_or_warning(
                host, ignore_errors,
                description='postcondition failed: {0}'.format(postcondition),
            )
            if not ignore_errors:
                state.trigger_callbacks('operation_host_error', host, op_hash)
                return False

        # Count success
        state.results[host]['ops'] += 1
        state.results[host]['success_ops'] += 1

        logger.info('{0}{1}'.format(
            host.print_prefix,
            click.style(
                'Success' if len(op_data['commands']) > 0 else 'No changes',
                'green',
            ),
        ))

        # Trigger any success handler
        if global_kwargs['on_success']:
            global_kwargs['on_success'](state, host, op_hash)

        state.trigger_callbacks('operation_host_success', host, op_hash)
        return True

    # Up error_ops & log
    state.results[host]['error_ops'] += 1

    log_error_or_warning(host, ignore_errors)

    # Always trigger any error handler
    if global_kwargs['on_error']:
        global_kwargs['on_error'](state, host, op_hash)

    # Ignored, op "completes" w/ ignored error
    if ignore_errors:
        state.results[host]['ops'] += 1

    # Unignored error -> False
    state.trigger_callbacks('operation_host_error', host, op_hash)
    if ignore_errors:
        return True
    return False


def _log_operation_start(op_meta):
    op_types = []
    if op_meta['serial']:
        op_types.append('serial')
    if op_meta['run_once']:
        op_types.append('run once')

    args = ''
    if op_meta['args']:
        args = '({0})'.format(', '.join(str(arg) for arg in op_meta['args']))

    logger.info('{0} {1} {2}'.format(
        click.style('--> Starting{0}operation:'.format(
            ' {0} '.format(', '.join(op_types)) if op_types else ' ',
        ), 'blue'),
        click.style(', '.join(op_meta['names']), bold=True),
        args,
    ))


def _run_server_ops(state, host, progress=None):
    '''
    Run all ops for a single server.
    '''

    logger.debug('Running all ops on {0}'.format(host))

    for op_hash in state.get_op_order():
        op_meta = state.get_op_meta(op_hash)
        _log_operation_start(op_meta)

        result = _run_server_op(state, host, op_hash)

        # Trigger CLI progress if provided
        if progress:
            progress((host, op_hash))

        if result is False:
            raise PyinfraError('Error in operation {0} on {1}'.format(
                ', '.join(op_meta['names']), host,
            ))

        if pyinfra.is_cli:
            click.echo(err=True)


def _run_serial_ops(state):
    '''
    Run all ops for all servers, one server at a time.
    '''

    for host in list(state.inventory.iter_active_hosts()):
        host_operations = product([host], state.get_op_order())
        with progress_spinner(host_operations) as progress:
            try:
                _run_server_ops(
                    state, host,
                    progress=progress,
                )
            except PyinfraError:
                state.fail_hosts({host})


def _run_no_wait_ops(state):
    '''
    Run all ops for all servers at once.
    '''

    hosts_operations = product(state.inventory.iter_active_hosts(), state.get_op_order())
    with progress_spinner(hosts_operations) as progress:
        # Spawn greenlet for each host to run *all* ops
        greenlets = [
            state.pool.spawn(
                _run_server_ops, state, host,
                progress=progress,
            )
            for host in state.inventory.iter_active_hosts()
        ]
        gevent.joinall(greenlets)


def _run_single_op(state, op_hash):
    '''
    Run a single operation for all servers. Can be configured to run in serial.
    '''

    state.trigger_callbacks('operation_start', op_hash)

    op_meta = state.get_op_meta(op_hash)
    _log_operation_start(op_meta)

    failed_hosts = set()

    if op_meta['serial']:
        with progress_spinner(state.inventory.iter_active_hosts()) as progress:
            # For each host, run the op
            for host in state.inventory.iter_active_hosts():
                result = _run_server_op(state, host, op_hash)
                progress(host)

                if not result:
                    failed_hosts.add(host)

    else:
        # Start with the whole inventory in one batch
        batches = [list(state.inventory.iter_active_hosts())]

        # If parallel set break up the inventory into a series of batches
        if op_meta['parallel']:
            parallel = op_meta['parallel']
            hosts = list(state.inventory.iter_active_hosts())

            batches = [
                hosts[i:i + parallel]
                for i in range(0, len(hosts), parallel)
            ]

        for batch in batches:
            with progress_spinner(batch) as progress:
                # Spawn greenlet for each host
                greenlet_to_host = {
                    state.pool.spawn(_run_server_op, state, host, op_hash): host
                    for host in batch
                }

                # Trigger CLI progress as hosts complete if provided
                for greenlet in gevent.iwait(greenlet_to_host.keys()):
                    host = greenlet_to_host[greenlet]
                    progress(host)

                # Get all the results
                for greenlet, host in six.iteritems(greenlet_to_host):
                    if not greenlet.get():
                        failed_hosts.add(host)

    # Now all the batches/hosts are complete, fail any failures
    state.fail_hosts(failed_hosts)

    if pyinfra.is_cli:
        click.echo(err=True)

    state.trigger_callbacks('operation_end', op_hash)


def run_ops(state, serial=False, no_wait=False):
    '''
    Runs all operations across all servers in a configurable manner.

    Args:
        state (``pyinfra.api.State`` obj): the deploy state to execute
        serial (boolean): whether to run operations host by host
        no_wait (boolean): whether to wait for all hosts between operations
    '''

    # Flag state as deploy in process
    state.deploying = True

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
