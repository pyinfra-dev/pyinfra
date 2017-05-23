# pyinfra
# File: pyinfra/api/operations.py
# Desc: Runs operations from pyinfra._ops in various modes (parallel, no_wait, serial)

from __future__ import print_function, unicode_literals

from socket import timeout as timeout_error
from types import FunctionType

import click
import gevent
import six

from pyinfra import logger
from pyinfra.api.exceptions import PyinfraError


def _run_op(state, host, op_hash):
    name = host.name

    # Noop for this host?
    if op_hash not in state.ops[name]:
        logger.info('[{0}] {1}'.format(
            click.style(name, bold=True),
            click.style(
                'Skipped',
                'blue',
            ),
        ))
        return True

    op_data = state.ops[name][op_hash]
    op_meta = state.op_meta[op_hash]

    stderr_buffer = []
    print_prefix = '{0}: '.format(click.style(name, bold=True))

    logger.debug('Starting operation {0} on {1}'.format(
        ', '.join(op_meta['names']), name,
    ))

    state.ops_run.add(op_hash)

    # ...loop through each command
    for i, command in enumerate(op_data['commands']):
        status = True

        sudo = op_meta['sudo']
        sudo_user = op_meta['sudo_user']
        su_user = op_meta['su_user']

        # As dicts, individual commands can override meta settings (ie on a
        # per-host basis generated during deploy).
        if isinstance(command, dict):
            if 'sudo' in command:
                sudo = command['sudo']

            if 'sudo_user' in command:
                sudo_user = command['sudo_user']

            if 'su_user' in command:
                su_user = command['su_user']

            command = command['command']

        # Now we attempt to execute the command

        # Tuples stand for callbacks & file uploads
        if isinstance(command, tuple):
            # If first element is function, it's a callback
            if isinstance(command[0], FunctionType):
                status = command[0](
                    state, state.inventory.get_host(name), name,
                    *command[1], **command[2]
                )

            # Non-function mean files to copy
            else:
                status = host.put_file(
                    state,
                    command[0], command[1],
                    sudo=sudo,
                    sudo_user=sudo_user,
                    su_user=su_user,
                    print_output=state.print_output,
                )

        # Must be a string/shell command: execute it on the server w/op-level preferences
        else:
            try:
                status, _, stderr = host.run_shell_command(
                    state,
                    command.strip(),
                    sudo=sudo,
                    sudo_user=sudo_user,
                    su_user=su_user,
                    timeout=op_meta['timeout'],
                    get_pty=op_meta['get_pty'],
                    env=op_data['env'],
                    print_output=state.print_output,
                )

                # Keep stderr in case of error
                stderr_buffer.extend(stderr)

            except timeout_error:
                timeout_message = 'Operation timeout after {0}s'.format(
                    op_meta['timeout'],
                )
                stderr_buffer.append(timeout_message)
                status = False

                # Print the timeout error as not printed by run_shell_command
                if state.print_output:
                    print('{0}{1}'.format(print_prefix, timeout_message))

        if status is False:
            break
        else:
            state.results[name]['commands'] += 1

    # Commands didn't break, so count our successes & return True!
    else:
        # Count success
        state.results[name]['ops'] += 1
        state.results[name]['success_ops'] += 1

        logger.info('[{0}] {1}'.format(
            click.style(name, bold=True),
            click.style(
                'Success' if len(op_data['commands']) > 0 else 'No changes',
                'green',
            ),
        ))

        return True

    # If the op failed somewhere, print stderr (if not already printed!)
    if not state.print_output:
        for line in stderr_buffer:
            print('    {0}{1}'.format(
                print_prefix,
                click.style(line, 'red'),
            ))

    # Up error_ops & log
    state.results[name]['error_ops'] += 1

    if op_meta['ignore_errors']:
        logger.warning('[{0}] {1}'.format(
            name,
            click.style('Error (ignored)', 'yellow'),
        ))
    else:
        logger.error('[{0}] {1}'.format(
            name,
            click.style('Error', 'red'),
        ))

    # Ignored, op "completes" w/ ignored error
    if op_meta['ignore_errors']:
        state.results[name]['ops'] += 1
        return None

    # Unignored error -> False
    return False


def _run_server_ops(state, host, progress=None):
    name = host.name

    logger.debug('Running all ops on {0}'.format(name))

    for op_hash in state.op_order:
        op_meta = state.op_meta[op_hash]

        logger.info('{0} {1} on {2}'.format(
            click.style('Starting operation:', 'blue'),
            click.style(', '.join(op_meta['names']), bold=True),
            click.style(name, bold=True),
        ))

        result = _run_op(state, host, op_hash)

        # Trigger CLI progress if provided
        if progress:
            progress()

        if result is False:
            raise PyinfraError('Error in operation {0} on {1}'.format(
                ', '.join(op_meta['names']), name,
            ))

        if state.print_lines:
            print()


def run_ops(state, serial=False, no_wait=False, progress=None):
    '''
    Runs all operations across all servers in a configurable manner.

    Args:
        state (``pyinfra.api.State`` obj): the deploy state to execute
        serial (boolean): whether to run operations host by host
        no_wait (boolean): whether to wait for all hosts between operations
    '''

    # Run all ops, but server by server
    if serial:
        for host in state.inventory:
            try:
                _run_server_ops(
                    state, host,
                    progress=progress,
                )
            except PyinfraError:
                state.fail_hosts({host.name})

        return

    # Run all the ops on each server in parallel (not waiting at each operation)
    elif no_wait:
        # Spawn greenlet for each host to run *all* ops
        greenlets = [
            state.pool.spawn(
                _run_server_ops, state, host,
                progress=progress,
            )
            for host in state.inventory
        ]
        gevent.joinall(greenlets)
        return

    # Default: run all ops in order, waiting at each for all servers to complete
    for op_hash in state.op_order:
        op_meta = state.op_meta[op_hash]

        op_types = []

        if op_meta['serial']:
            op_types.append('serial')

        if op_meta['run_once']:
            op_types.append('run once')

        logger.info('{0} {1} {2}'.format(
            click.style('Starting{0}operation:'.format(
                ' {0} '.format(', '.join(op_types)) if op_types else ' ',
            ), 'blue'),
            click.style(', '.join(op_meta['names']), bold=True),
            tuple(op_meta['args']) if op_meta['args'] else '',
        ))

        failed_hosts = set()

        if op_meta['serial']:
            # For each host, run the op
            for host in state.inventory:
                result = _run_op(state, host, op_hash)

                # Trigger CLI progress if provided
                if progress:
                    progress()

                if not result:
                    failed_hosts.add(host.name)

        else:
            # Spawn greenlet for each host
            greenlets = {
                host.name: state.pool.spawn(
                    _run_op, state, host, op_hash,
                )
                for host in state.inventory
            }

            for _ in gevent.iwait(greenlets.values()):
                # Trigger CLI progress if provided
                if progress:
                    progress()

            # Get all the results
            for hostname, greenlet in six.iteritems(greenlets):
                if not greenlet.get():
                    failed_hosts.add(hostname)

        if not op_meta['ignore_errors']:
            state.fail_hosts(failed_hosts)

        if state.print_lines:
            print()
