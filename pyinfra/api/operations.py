# pyinfra
# File: pyinfra/api/operations.py
# Desc: Runs operations from pyinfra._ops in various modes (parallel, nowait, serial)

from __future__ import division

from types import FunctionType
from socket import timeout as timeout_error

from gevent import joinall
from termcolor import colored

from pyinfra import logger
from pyinfra.api.exceptions import PyinfraError

from .ssh import run_shell_command, put_file


def _run_op(state, hostname, op_hash, print_output=False):
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
                    print_output=print_output,
                    print_prefix=print_prefix,
                    *command[1], **command[2]
                )

            # Non-function mean files to copy
            else:
                status = put_file(
                    state, hostname, *command,
                    sudo=sudo,
                    sudo_user=sudo_user,
                    print_output=print_output,
                    print_prefix=print_prefix
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
                    print_output=print_output,
                    print_prefix=print_prefix
                )

                # Keep stderr in case of error
                stderr_buffer.extend(stderr)
                status = channel.exit_status <= 0

            except timeout_error:
                timeout_message = 'Operation timeout after {0}s'.format(op_meta['timeout'])
                stderr_buffer.append(timeout_message)
                status = False

                # Print the timeout error as not printed by run_shell_command
                if print_output:
                    print u'{0}{1}'.format(print_prefix, timeout_message)

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
    if not print_output:
        for line in stderr_buffer:
            print u'    {0}{1}'.format(
                print_prefix,
                colored(line, 'red')
            )

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


def _run_server_ops(state, hostname, print_output, print_lines):
    logger.debug('Running all ops on {}'.format(hostname))
    for op_hash in state.op_order:
        op_meta = state.op_meta[op_hash]

        logger.info('{0} {1} on {2}'.format(
            colored('Starting operation:', 'blue'),
            colored(', '.join(op_meta['names']), attrs=['bold']),
            colored(hostname, attrs=['bold'])
        ))

        result = _run_op(state, hostname, op_hash, print_output)
        if result is False:
            raise PyinfraError('Error in operation {0} on {1}'.format(
                ', '.join(op_meta['names']), hostname
            ))

        if print_lines:
            print


def run_ops(
    state, serial=False, nowait=False,
    print_output=False, print_lines=False
):
    '''
    Runs all operations across all servers in a configurable manner.

    Args:
        state (``pyinfra.api.State`` obj): the deploy state to execute
        serial (boolean): whether to run operations host by host
        nowait (boolean): whether to wait for all hosts between operations
    '''

    hosts = state.inventory

    # Run all ops, but server by server
    if serial:
        for host in hosts:
            _run_server_ops(
                state, host.ssh_hostname,
                print_output=print_output, print_lines=print_lines
            )
        return

    # Run all the ops on each server in parallel (not waiting at each operation)
    elif nowait:
        # Spawn greenlet for each host to run *all* ops
        greenlets = [
            state.pool.spawn(
                _run_server_ops, state, host.ssh_hostname,
                print_output=print_output, print_lines=print_lines
            )
            for host in hosts
        ]
        joinall(greenlets)
        return

    # Run all ops in order, waiting at each for all servers to complete
    remove_hosts = set()
    for op_hash in state.op_order:
        op_meta = state.op_meta[op_hash]

        op_types = []
        if op_meta['serial']:
            op_types.append('serial')
        if op_meta['run_once']:
            op_types.append('run once')

        logger.info('{0} {1}'.format(
            colored('Starting{0}operation:'.format(
                ' {0} '.format(', '.join(op_types)) if op_types else ' '
            ), 'blue'),
            colored(', '.join(op_meta['names']), attrs=['bold'])
        ))

        op_hosts = set(list(host.ssh_hostname for host in hosts)) - remove_hosts
        successful_hosts = []
        failed_hosts = []

        if op_meta['serial']:
            # For each host, run the op
            for hostname in op_hosts:
                result = _run_op(state, hostname, op_hash, print_output=print_output)

                if result:
                    successful_hosts.append(hostname)
                else:
                    failed_hosts.append(hostname)

        else:
            # Spawn greenlet for each host
            greenlet_hosts = [
                (hostname, state.pool.spawn(
                    _run_op, state, hostname, op_hash, print_output=print_output
                ))
                for hostname in op_hosts
            ]

            # Get all the results
            for (hostname, greenlet) in greenlet_hosts:
                if greenlet.get():
                    successful_hosts.append(hostname)
                else:
                    failed_hosts.append(hostname)

        if not op_meta['ignore_errors']:
            # Don't continue operations on failed/non-ignore hosts
            for hostname in failed_hosts:
                remove_hosts.add(hostname)

            # Check we're not above the fail percent
            if state.config.FAIL_PERCENT is not None:
                percent_failed = (1 - len(successful_hosts) / len(hosts)) * 100

                if percent_failed > state.config.FAIL_PERCENT:
                    raise PyinfraError('Over {0}% of hosts failed'.format(
                        state.config.FAIL_PERCENT
                    ))

            # No hosts left!
            if not successful_hosts:
                raise PyinfraError('No hosts remaining')

        if print_lines:
            print
