# pyinfra
# File: pyinfra/api/operations.py
# Desc: Runs operations from pyinfra._ops in various modes (parallel, no_wait, serial)

from __future__ import unicode_literals, print_function

from types import FunctionType
from socket import timeout as timeout_error

from gevent import joinall
from termcolor import colored

from pyinfra import logger
from pyinfra.api.exceptions import PyinfraError

from .ssh import run_shell_command, put_file


def _run_op(state, hostname, op_hash):
    # Noop for this host?
    if op_hash not in state.ops[hostname]:
        logger.debug('(Skipping) no op {0} on {1}'.format(op_hash, hostname))
        return True

    op_data = state.ops[hostname][op_hash]
    op_meta = state.op_meta[op_hash]

    stderr_buffer = []
    print_prefix = '{}: '.format(hostname, attrs=['bold'])

    skip = False

    # If run once & already run, flag to skip
    if op_meta['run_once'] and op_hash in state.ops_run:
        skip = True
        logger.debug('Skipping {0} on {1}, run once'.format(op_hash, hostname))
    else:
        logger.debug('Starting operation {0} on {1}'.format(
            ', '.join(op_meta['names']), hostname
        ))

    state.ops_run.add(op_hash)

    # ...loop through each command
    for i, command in enumerate(op_data['commands']):
        status = True

        sudo = op_meta['sudo']
        sudo_user = op_meta['sudo_user']

        # As dicts, individual commands can override meta settings (ie on a per-host
        # basis generated during deploy).
        if isinstance(command, dict):
            if 'sudo' in command:
                sudo = command['sudo']
            if 'sudo_user' in command:
                sudo_user = command['sudo_user']

            command = command['command']

        if skip:
            # Not continue because we need to +commands below
            pass

        # Tuples stand for callbacks & file uploads
        elif isinstance(command, tuple):
            # If first element is function, it's a callback
            if isinstance(command[0], FunctionType):
                status = command[0](
                    state, state.inventory[hostname], hostname,
                    *command[1], **command[2]
                )

            # Non-function mean files to copy
            else:
                status = put_file(
                    state, hostname, *command,
                    sudo=sudo,
                    sudo_user=sudo_user,
                    print_output=state.print_output
                )

        # Must be a string/shell command: execute it on the server w/op-level preferences
        else:
            try:
                channel, _, stderr = run_shell_command(
                    state, hostname, command.strip(),
                    sudo=sudo,
                    sudo_user=sudo_user,
                    timeout=op_meta['timeout'],
                    env=op_data['env'],
                    print_output=state.print_output
                )

                # Keep stderr in case of error
                stderr_buffer.extend(stderr)
                status = channel.exit_status <= 0

            except timeout_error:
                timeout_message = 'Operation timeout after {0}s'.format(op_meta['timeout'])
                stderr_buffer.append(timeout_message)
                status = False

                # Print the timeout error as not printed by run_shell_command
                if state.print_output:
                    print('{0}{1}'.format(print_prefix, timeout_message))

        if status is False:
            break
        else:
            state.results[hostname]['commands'] += 1

    # Commands didn't break, so count our successes & return True!
    else:
        # Count success
        state.results[hostname]['ops'] += 1
        state.results[hostname]['success_ops'] += 1

        if not skip:
            logger.info('[{0}] {1}'.format(
                colored(hostname, attrs=['bold']),
                colored(
                    'Success' if len(op_data['commands']) > 0 else 'No changes',
                    'green'
                )
            ))

        return True

    # If the op failed somewhere, print stderr (if not already printed!)
    if not state.print_output:
        for line in stderr_buffer:
            print('    {0}{1}'.format(
                print_prefix,
                colored(line, 'red')
            ))

    # Up error_ops & log
    state.results[hostname]['error_ops'] += 1

    if op_meta['ignore_errors']:
        logger.warning('[{0}] {1}'.format(
            hostname,
            colored('Error (ignored)', 'yellow')
        ))
    else:
        logger.error('[{0}] {1}'.format(
            hostname,
            colored('Error', 'red')
        ))

    # Ignored, op "completes" w/ ignored error
    if op_meta['ignore_errors']:
        state.results[hostname]['ops'] += 1
        return None

    # Unignored error -> False
    return False


def _run_server_ops(state, hostname):
    logger.debug('Running all ops on {}'.format(hostname))
    for op_hash in state.op_order:
        op_meta = state.op_meta[op_hash]

        logger.info('{0} {1} on {2}'.format(
            colored('Starting operation:', 'blue'),
            colored(', '.join(op_meta['names']), attrs=['bold']),
            colored(hostname, attrs=['bold'])
        ))

        result = _run_op(state, hostname, op_hash)
        if result is False:
            raise PyinfraError('Error in operation {0} on {1}'.format(
                ', '.join(op_meta['names']), hostname
            ))

        if state.print_lines:
            print()


def run_ops(state, serial=False, no_wait=False):
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
            _run_server_ops(state, host.name)
        return

    # Run all the ops on each server in parallel (not waiting at each operation)
    elif no_wait:
        # Spawn greenlet for each host to run *all* ops
        greenlets = [
            state.pool.spawn(_run_server_ops, state, host.name)
            for host in state.inventory
        ]
        joinall(greenlets)
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
            colored('Starting{0}operation:'.format(
                ' {0} '.format(', '.join(op_types)) if op_types else ' '
            ), 'blue'),
            colored(', '.join(op_meta['names']), attrs=['bold']),
            tuple(op_meta['args']) if op_meta['args'] else ''
        ))

        failed_hosts = set()

        if op_meta['serial']:
            # For each host, run the op
            for host in state.inventory:
                result = _run_op(state, host.name, op_hash)

                if not result:
                    failed_hosts.add(host.name)

        else:
            # Spawn greenlet for each host
            greenlet_hosts = [
                (host.name, state.pool.spawn(
                    _run_op, state, host.name, op_hash
                ))
                for host in state.inventory
            ]

            # Get all the results
            for (hostname, greenlet) in greenlet_hosts:
                if not greenlet.get():
                    failed_hosts.add(hostname)

        if not op_meta['ignore_errors']:
            state.fail_hosts(failed_hosts)

        if state.print_lines:
            print()
