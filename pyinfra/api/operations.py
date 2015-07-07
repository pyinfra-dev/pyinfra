# pyinfra
# File: pyinfra/api/operations.py
# Desc: Runs operations from pyinfra._ops in various modes (parallel, parallel+nowait, serial)

from __future__ import division

from types import FunctionType

from gevent import joinall
from termcolor import colored

from pyinfra import state, logger

from .ssh import run_shell_command, put_file


def _run_op(hostname, op_hash, print_output=False):
    # Noop for this host?
    if op_hash not in state.ops[hostname]:
        logger.debug('(Skipping) no op {0} on {1}'.format(op_hash, hostname))
        return True

    op_data = state.ops[hostname][op_hash]
    op_meta = state.op_meta[op_hash]

    # Op is run_once, have we run it elsewhere?
    if op_meta['run_once']:
        if op_hash in state.ops_run:
            logger.debug('(Skipping) run_once op {0} already started on {1}'.format(op_hash, hostname))
            return

    stdout_buffer = []
    stderr_buffer = []
    print_prefix = '[{}] '.format(colored(hostname, attrs=['bold']))

    logger.debug('Starting operation {0} on {1}'.format(', '.join(op_meta['names']), hostname))
    if op_hash not in state.ops_run:
        state.ops_run.append(op_hash)

    # ...loop through each command
    for i, command in enumerate(op_data['commands']):
        status = True

        # Tuples stand for callbacks & file uploads
        if isinstance(command, tuple):
            # If first element is function, it's a callback
            if isinstance(command[0], FunctionType):
                status = command[0](hostname, state.inventory[hostname])

            # Non-function mean files to copy
            else:
                status = put_file(
                    hostname, *command,
                    sudo=op_meta['sudo'],
                    sudo_user=op_meta['sudo_user'],
                    print_output=print_output,
                    print_prefix=print_prefix
                )

        # Must be a string/shell command: execute it on the server w/op-level preferences
        else:
            channel, stdout, stderr = run_shell_command(
                hostname, command.strip(),
                sudo=op_meta['sudo'],
                sudo_user=op_meta['sudo_user'],
                env=op_data['env'],
                print_output=print_output,
                print_prefix=print_prefix
            )

            # If not iterated, do so to get an exit status
            if not print_output:
                stdout_buffer.extend(stdout)
                stderr_buffer.extend(stderr)

            status = channel.exit_status <= 0

        if status is False:
            break
        else:
            state.results[hostname]['commands'] += 1

    # Commands didn't break, so count our successes & return True!
    else:
        # Count success
        state.results[hostname]['ops'] += 1
        state.results[hostname]['success_ops'] += 1

        logger.info('[{0}] {1}'.format(
            colored(hostname, attrs=['bold']),
            colored('Success' if len(op_data['commands']) > 0 else 'No changes', 'green')
        ))

        return True

    # If the op failed somewhere, print stderr (if not already printed!)
    if not print_output:
        for line in stderr_buffer:
            print u'{0}{1}'.format(
                print_prefix,
                colored(line, 'red')
            )

    # Up error_ops & log
    state.results[hostname]['error_ops'] += 1

    error_text = '{0}{1}'.format(colored(''), print_prefix)
    if op_meta['ignore_errors']:
        logger.warning('{0}{1}'.format(
            error_text,
            colored('Error (ignored)', 'yellow')
        ))
    else:
        logger.critical('{0}{1}'.format(
            error_text,
            colored('Error', 'red')
        ))

    # Ignored, op "completes" w/ ignored error
    if op_meta['ignore_errors']:
        state.results[hostname]['ops'] += 1
        return None

    # Unignored error -> False
    return False


def _run_server_ops(hostname, print_output):
    logger.debug('Running all ops on {}'.format(hostname))
    for op_hash in state.op_order:
        op_meta = state.op_meta[op_hash]

        logger.info('{0} {1} on {2}'.format(
            colored('Starting operation:', 'blue'),
            colored(', '.join(op_meta['names']), attrs=['bold']),
            colored(hostname, attrs=['bold'])
        ))

        result = _run_op(hostname, op_hash, print_output)
        if result is False:
            logger.critical('Error in operation {0} on {1}, exiting...'.format(
                ', '.join(op_meta['names']), hostname
            ))
            return


def run_ops(hosts=None, serial=False, nowait=False, print_output=False):
    '''Runs all operations across all servers in a configurable manner.'''
    hosts = hosts or state.inventory

    # Run all ops, but server by server
    if serial:
        for host in hosts:
            _run_server_ops(host.ssh_hostname, print_output=print_output)
        return

    # Run all the ops on each server in parallel (not waiting at each operation)
    elif nowait:
        # Spawn greenlet for each host to run *all* ops
        greenlets = [
            state.pool.spawn(_run_server_ops, host.ssh_hostname, print_output=print_output)
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
                ' {} '.format(', '.join(op_types)) if op_types else ' '
            ), 'blue'),
            colored(', '.join(op_meta['names']), attrs=['bold'])
        ))

        op_hosts = set(list(host.ssh_hostname for host in hosts)) - remove_hosts
        successful_hosts = []
        failed_hosts = []

        if op_meta['serial']:
            # For each host, run the op
            for hostname in op_hosts:
                result = _run_op(hostname, op_hash, print_output=print_output)

                if result:
                    successful_hosts.append(hostname)
                else:
                    failed_hosts.append(hostname)
        else:
            # Spawn greenlet for each host
            greenlet_hosts = [
                (hostname, state.pool.spawn(_run_op, hostname, op_hash, print_output=print_output))
                for hostname in op_hosts
            ]

            # Get all the results
            for (hostname, greenlet) in greenlet_hosts:
                if greenlet.get():
                    successful_hosts.append(hostname)
                else:
                    failed_hosts.append(hostname)

        if op_meta['ignore_errors']:
            continue

        # Don't continue operations on failed/non-ignore hosts
        for hostname in failed_hosts:
            remove_hosts.add(hostname)

        # Check we're not above the fail percent
        if state.config.FAIL_PERCENT:
            percent_failed = (1 - len(successful_hosts) / len(hosts)) * 100

            if percent_failed > state.config.FAIL_PERCENT:
                logger.critical(
                    'Over {0}% of hosts failed, exiting'.format(state.config.FAIL_PERCENT)
                )
                break

        # No hosts left!
        if not successful_hosts:
            logger.critical('No hosts remaining, exiting...')
            break
