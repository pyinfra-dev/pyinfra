from __future__ import print_function, unicode_literals

from itertools import product
from socket import (
    error as socket_error,
    timeout as timeout_error,
)
from types import FunctionType

import click
import gevent
import six

from paramiko import SSHException

import pyinfra

from pyinfra import logger
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.util import format_exception, log_host_command_error
from pyinfra.progress import progress_spinner


def _run_server_op(state, host, op_hash):
    # Noop for this host?
    if op_hash not in state.ops[host]:
        logger.info('{0}{1}'.format(
            host.print_prefix,
            click.style(
                'Skipped',
                'blue',
            ),
        ))
        return True

    op_data = state.ops[host][op_hash]
    op_meta = state.op_meta[op_hash]

    logger.debug('Starting operation {0} on {1}'.format(
        ', '.join(op_meta['names']), host,
    ))

    state.ops_run.add(op_hash)

    # ...loop through each command
    for i, command in enumerate(op_data['commands']):
        status = False

        shell_executable = op_meta['shell_executable']
        sudo = op_meta['sudo']
        sudo_user = op_meta['sudo_user']
        su_user = op_meta['su_user']
        preserve_sudo_env = op_meta['preserve_sudo_env']
        success_exit_codes = op_meta['success_exit_codes']

        # As dicts, individual commands can override meta settings (ie on a
        # per-host basis generated during deploy).
        if isinstance(command, dict):
            if 'sudo' in command:
                sudo = command['sudo']

            if 'sudo_user' in command:
                sudo_user = command['sudo_user']

            if 'su_user' in command:
                su_user = command['su_user']

            if 'shell_executable' in command:
                shell_executable = command['shell_executable']

            if 'success_exit_codes' in command:
                success_exit_codes = command['success_exit_codes']

            command = command['command']

        # Now we attempt to execute the command

        # Tuples stand for callbacks & file uploads
        if isinstance(command, tuple):
            # If first element is function, it's a callback
            if isinstance(command[0], FunctionType):
                func, args, kwargs = command

                try:
                    status = func(
                        state, host,
                        *args, **kwargs
                    )

                # Custom functions could do anything, so expect anything!
                except Exception as e:
                    logger.error('{0}{1}'.format(
                        host.print_prefix,
                        click.style(
                            'Unexpected error in Python callback: {0}'.format(
                                format_exception(e),
                            ),
                            'red',
                        ),
                    ))

            # Non-function mean files to copy
            else:
                method_type, first_file, second_file = command

                if method_type == 'upload':
                    method = host.put_file
                elif method_type == 'download':
                    method = host.get_file
                else:
                    raise TypeError('{0} is an invalid pyinfra command!'.format(command))

                try:
                    status = method(
                        state,
                        first_file,
                        second_file,
                        sudo=sudo,
                        sudo_user=sudo_user,
                        su_user=su_user,
                        shell_executable=shell_executable,
                        print_output=state.print_output,
                        print_input=state.print_input,
                    )

                except (timeout_error, socket_error, SSHException, IOError) as e:
                    log_host_command_error(
                        host,
                        e,
                        timeout=op_meta['timeout'],
                    )

        # Must be a string/shell command: execute it on the server w/op-level preferences
        elif isinstance(command, six.string_types):
            combined_output_lines = []

            try:
                status, combined_output_lines = host.run_shell_command(
                    state,
                    command.strip(),
                    sudo=sudo,
                    sudo_user=sudo_user,
                    use_sudo_login=op_meta['use_sudo_login'],
                    su_user=su_user,
                    use_su_login=op_meta['use_su_login'],
                    preserve_sudo_env=preserve_sudo_env,
                    shell_executable=shell_executable,
                    timeout=op_meta['timeout'],
                    get_pty=op_meta['get_pty'],
                    env=op_meta['env'],
                    stdin=op_meta['stdin'],
                    success_exit_codes=success_exit_codes,
                    print_output=state.print_output,
                    print_input=state.print_input,
                    return_combined_output=True,
                )

            except (timeout_error, socket_error, SSHException) as e:
                log_host_command_error(
                    host,
                    e,
                    timeout=op_meta['timeout'],
                )

            # If we failed and have no already printed the stderr, print it
            if status is False and not state.print_output:
                for type_, line in combined_output_lines:
                    if type_ == 'stderr':
                        logger.error('{0}{1}'.format(
                            host.print_prefix,
                            click.style(line, 'red'),
                        ))
                    else:
                        logger.error('{0}{1}'.format(
                            host.print_prefix,
                            line,
                        ))
        else:
            raise TypeError('{0} is an invalid pyinfra command!'.format(command))

        # Break the loop to trigger a failure
        if status is False:
            break
        else:
            state.results[host]['commands'] += 1

    # Commands didn't break, so count our successes & return True!
    else:
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
        if op_meta['on_success']:
            op_meta['on_success'](state, host, op_hash)

        return True

    # Up error_ops & log
    state.results[host]['error_ops'] += 1

    if op_meta['ignore_errors']:
        logger.warning('{0}{1}'.format(
            host.print_prefix,
            click.style('Error (ignored)', 'yellow'),
        ))
    else:
        logger.error('{0}{1}'.format(
            host.print_prefix,
            click.style('Error', 'red'),
        ))

    # Always trigger any error handler
    if op_meta['on_error']:
        op_meta['on_error'](state, host, op_hash)

    # Ignored, op "completes" w/ ignored error
    if op_meta['ignore_errors']:
        state.results[host]['ops'] += 1

    # Unignored error -> False
    return False


def _run_server_ops(state, host, progress=None):
    '''
    Run all ops for a single server.
    '''

    logger.debug('Running all ops on {0}'.format(host))

    for op_hash in state.get_op_order():
        op_meta = state.op_meta[op_hash]

        logger.info('--> {0} {1} on {2}'.format(
            click.style('--> Starting operation:', 'blue'),
            click.style(', '.join(op_meta['names']), bold=True),
            click.style(host.name, bold=True),
        ))

        result = _run_server_op(state, host, op_hash)

        # Trigger CLI progress if provided
        if progress:
            progress((host, op_hash))

        if result is False:
            raise PyinfraError('Error in operation {0} on {1}'.format(
                ', '.join(op_meta['names']), host,
            ))

        if pyinfra.is_cli:
            click.echo()


def _run_serial_ops(state):
    '''
    Run all ops for all servers, one server at a time.
    '''

    for host in list(state.inventory):
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

    hosts_operations = product(state.inventory, state.get_op_order())
    with progress_spinner(hosts_operations) as progress:
        # Spawn greenlet for each host to run *all* ops
        greenlets = [
            state.pool.spawn(
                _run_server_ops, state, host,
                progress=progress,
            )
            for host in state.inventory
        ]
        gevent.joinall(greenlets)


def _run_single_op(state, op_hash):
    '''
    Run a single operation for all servers. Can be configured to run in serial.
    '''

    op_meta = state.op_meta[op_hash]

    op_types = []

    if op_meta['serial']:
        op_types.append('serial')

    if op_meta['run_once']:
        op_types.append('run once')

    logger.info('{0} {1} {2}'.format(
        click.style('--> Starting{0}operation:'.format(
            ' {0} '.format(', '.join(op_types)) if op_types else ' ',
        ), 'blue'),
        click.style(', '.join(op_meta['names']), bold=True),
        tuple(op_meta['args']) if op_meta['args'] else '',
    ))

    failed_hosts = set()

    if op_meta['serial']:
        with progress_spinner(state.inventory) as progress:
            # For each host, run the op
            for host in state.inventory:
                result = _run_server_op(state, host, op_hash)
                progress(host)

                if not result:
                    failed_hosts.add(host)

    else:
        # Start with the whole inventory in one batch
        batches = [state.inventory]

        # If parallel set break up the inventory into a series of batches
        if op_meta['parallel']:
            parallel = op_meta['parallel']
            hosts = list(state.inventory)

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
    if not op_meta['ignore_errors']:
        state.fail_hosts(failed_hosts)

    if pyinfra.is_cli:
        click.echo()


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
    for op_hash in state.get_op_order():
        _run_single_op(state, op_hash)
