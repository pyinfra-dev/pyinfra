# pyinfra
# File: pyinfra/api/operations.py
# Desc: Runs operations from pyinfra._ops in various modes (parallel, parallel+nowait, serial)

from types import FunctionType

from gevent import joinall
from termcolor import colored

import pyinfra
from pyinfra import config, logger

from .ssh import run_shell_command, put_file


def run_op(hostname, op_hash, print_output=False):
    '''Runs a single operation on a remote server.'''
    # Noop for this host?
    if op_hash not in pyinfra._ops[hostname]:
        logger.debug('(Skipping) no op {0} on {1}'.format(op_hash, hostname))
        return

    op_data = pyinfra._ops[hostname][op_hash]
    op_meta = pyinfra._op_meta[op_hash]

    # Op is run_once, have we run it elsewhere?
    if op_meta['run_once']:
        if op_hash in pyinfra._ops_run:
            logger.debug('(Skipping) run_once op {0} already started on {1}'.format(op_hash, hostname))
            return

    stdout_buffer = []
    stderr_buffer = []
    print_prefix = '[{}] '.format(colored(hostname, attrs=['bold']))

    logger.debug('Starting operation {0} on {1}'.format(', '.join(op_meta['names']), hostname))
    if op_hash not in pyinfra._ops_run:
        pyinfra._ops_run.append(op_hash)

    # ...loop through each command
    for i, command in enumerate(op_data['commands']):
        status = True

        # Tuples stand for callbacks & file uploads
        if isinstance(command, tuple):
            # If first element is function, it's a callback
            if isinstance(command[0], FunctionType):
                status = command[0](hostname, **command[1])

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

            # Iterate through outputs to get an exit status
            # this iterates as the socket data comes in, which gevent patches
            for line in stdout:
                line = line.strip()
                stdout_buffer.append(line)
                if print_output:
                    print u'{0}{1}'.format(print_prefix, line)

            for line in stderr:
                line = line.strip()
                stderr_buffer.append(line)
                if print_output:
                    print u'{0}{1}'.format(
                        print_prefix,
                        colored(line, 'red')
                    )

            status = channel.exit_status <= 0

        if status is False:
            break
        else:
            pyinfra._results[hostname]['commands'] += 1

    # Commands didn't break, so count our successes & return True!
    else:
        # Count success
        pyinfra._results[hostname]['ops'] += 1
        pyinfra._results[hostname]['success_ops'] += 1

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
    pyinfra._results[hostname]['error_ops'] += 1
    logger.info('[{0}] {1}'.format(
        colored(hostname, attrs=['bold']),
        colored('Error{0}'.format(
            ' (ignored)' if op_meta['ignore_errors'] else ''
        ), 'yellow')
    ))

    # Ignored, op "completes" w/ ignored error
    if op_meta['ignore_errors']:
        pyinfra._results[hostname]['ops'] += 1
        return None

    # Unignored error -> False
    return False


def run_server_ops(hostname, print_output):
    '''Runs all operations for a single server.'''
    logger.debug('Running all ops on {}'.format(hostname))
    for op_hash in pyinfra._op_order:
        op_meta = pyinfra._op_meta[op_hash]

        logger.info('{0} {1} on {2}'.format(
            colored('Starting operation:', 'blue'),
            colored(', '.join(op_meta['names']), attrs=['bold']),
            colored(hostname, attrs=['bold'])
        ))

        result = run_op(hostname, op_hash, print_output)
        if result is False:
            logger.critical('Error in operation {0} on {1}, exiting...'.format(
                ', '.join(op_meta['names']), hostname
            ))
            return


def run_ops(serial=False, nowait=False, print_output=False):
    '''Runs all operations across all servers in a configurable manner.'''
    # Run all ops, but server by server
    if serial:
        for hostname in config.SSH_HOSTS:
            run_server_ops(hostname, print_output=print_output)
        return

    # Run all the ops on each server in parallel (not waiting at each operation)
    elif nowait:
        # Spawn greenlet for each host to run *all* ops
        greenlets = [
            pyinfra._pool.spawn(run_server_ops, hostname, print_output=print_output)
            for hostname in config.SSH_HOSTS
        ]
        joinall(greenlets)
        return

    # Run all ops in order, waiting at each for all servers to complete
    for op_hash in pyinfra._op_order:
        op_meta = pyinfra._op_meta[op_hash]

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

        results = []

        if op_meta['serial']:
            # For each host, run the op
            for hostname in config.SSH_HOSTS:
                result = run_op(hostname, op_hash, print_output=print_output)
                results.append(result)

                # If we failed break to be handled as op error
                if result is False:
                    break

        else:
            # Spawn greenlet for each host
            greenlet_hosts = [
                pyinfra._pool.spawn(run_op, hostname, op_hash, print_output=print_output)
                for hostname in config.SSH_HOSTS
            ]

            # Get all the results
            results = [greenlet.get() for greenlet in greenlet_hosts]

        # Any False = unignored error, so we stop everything here
        if False in results:
            logger.critical('Error in operation {}, exiting...'.format(', '.join(op_meta['names'])))
            break
