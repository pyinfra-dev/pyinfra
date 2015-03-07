# pyinfra
# File: pyinfra/api/operations.py
# Desc: Runs operations from pyinfra._ops in various modes (parallel, parallel+nowait, serial)

from termcolor import colored

import pyinfra
from pyinfra import config, logger


def run_op(hostname, op_hash, print_output=False):
    '''Runs a single operation on a remote server.'''
    ops = pyinfra._ops[hostname]

    if op_hash not in ops:
        logger.debug('(Skipping) no op {} on {}'.format(op_hash, hostname))
        return

    connection = pyinfra._connections[hostname]
    op_data = pyinfra._ops[hostname][op_hash]
    op_meta = pyinfra._op_meta[op_hash]

    stdout_buffer = []
    stderr_buffer = []
    print_prefix = '[{}] '.format(colored(hostname, attrs=['bold']))

    logger.debug('Starting operation {} on {}'.format(', '.join(op_meta['names']), hostname))
    # ...loop through each command, execute it on the server w/op-level preferences
    for i, command in enumerate(op_data['commands']):
        logger.debug('Running command on {0}: "{1}"'.format(hostname, command))
        logger.debug('Command sudo?: {}, sudo user: {}, env: {}'.format(
            op_meta['sudo'], op_meta['sudo_user'], op_data['env']
        ))

        # Use env & build our actual command
        env_string = ' '.join([
            '{}={}'.format(key, value)
            for key, value in op_data['env'].iteritems()
        ])
        command = '{} {}'.format(env_string, command)

        # Escape "'s
        command = command.replace('"', '\\"')

        # No sudo, just bash wrap the command
        if not op_meta['sudo']:
            command = 'bash -c "{}"'.format(command)
        # Otherwise, work out sudo
        else:
            # Sudo with a user, then bash
            if op_meta['sudo_user']:
                command = 'sudo -u {} -S bash -c "{}"'.format(op_meta['sudo_user'], command)
            # Sudo then bash
            else:
                command = 'sudo -S bash -c "{}"'.format(command)

        if print_output:
            print '{}>>> {}'.format(print_prefix, command)

        # Run it! Get stdout, stderr & the underlying channel
        _, stdout, stderr = connection.exec_command(command)
        channel = stdout.channel

        # Iterate through outputs to get an exit status
        # this iterates as the socket data comes in, which gevent patches
        for line in stdout:
            line = line.strip()
            stdout_buffer.append(line)
            if print_output:
                print '{}{}'.format(print_prefix, line)

        for line in stderr:
            line = line.strip()
            stderr_buffer.append(line)
            if print_output:
                print '{}{}: {}'.format(
                    print_prefix,
                    colored('stderr', 'red', attrs=['bold']),
                    line
                )

        if channel.exit_status <= 0:
            pyinfra._results[hostname]['commands'] += 1
        else:
            break

    # Commands didn't break, so count our successes & return True!
    else:
        # Count success
        pyinfra._results[hostname]['ops'] += 1
        pyinfra._results[hostname]['success_ops'] += 1

        logger.info('[{}] {}'.format(
            colored(hostname, attrs=['bold']),
            colored('Success' if len(op_data['commands']) > 0 else 'No changes', 'green')
        ))

        return True

    # If the op failed somewhere, print stderr (if not already printed!)
    if not print_output:
        for line in stderr_buffer:
            print '{}{}: {}'.format(
                print_prefix,
                colored('stderr', 'red', attrs=['bold']),
                line
            )

    # Up error_ops & log
    pyinfra._results[hostname]['error_ops'] += 1
    logger.info('[{}] {}'.format(
        colored(hostname, attrs=['bold']),
        colored('Error{}'.format(
            ' (ignored)' if op_meta['ignore_errors'] else ''
        ), 'yellow')
    ))

    # Ignored, op "completes" w/ ignored error
    if op_meta['ignore_errors']:
        pyinfra._results[hostname]['ops'] += 1
        return None

    # Unignored error -> False
    return False


def _run_server_ops(hostname, print_output):
    logger.debug('Running all ops on {}'.format(hostname))
    for op_hash in pyinfra._op_order:
        op_meta = pyinfra._op_meta[op_hash]

        logger.info('{} {} on {}'.format(
            colored('Starting operation:', 'blue'),
            colored(', '.join(op_meta['names']), attrs=['bold']),
            colored(hostname, attrs=['bold'])
        ))

        result = run_op(hostname, op_hash, print_output)
        if result is False:
            logger.critical('Error in operation {} on {}, exiting...'.format(
                ', '.join(op_meta['names']), hostname
            ))
            return

def run_ops(serial=False, nowait=False, print_output=False):
    '''Runs all operations across all servers in a configurable manner.'''
    # Run all ops, but server by server
    if serial:
        [_run_server_ops(hostname, print_output=print_output) for hostname in config.SSH_HOSTS]
        return

    # Run all the ops on each server in parallel (not waiting at each operation)
    elif nowait:
        # Spawn greenlet for each host to run *all* ops
        greenlet_hosts = {
            pyinfra._pool.spawn(_run_server_ops, hostname, print_output=print_output): hostname
            for hostname in config.SSH_HOSTS
        }
        [greenlet.join() for greenlet in greenlet_hosts.keys()]
        return

    # Run all ops in order, waiting at each for all servers to complete
    for op_hash in pyinfra._op_order:
        op_meta = pyinfra._op_meta[op_hash]

        logger.info('{} {}'.format(
            colored('Starting operation:', 'blue'),
            colored(', '.join(op_meta['names']), attrs=['bold']),
        ))

        # Spawn greenlet for each host
        greenlet_hosts = {
            pyinfra._pool.spawn(run_op, hostname, op_hash, print_output=print_output): hostname
            for hostname in config.SSH_HOSTS
        }

        # Get all the results
        results = [greenlet.get() for greenlet in greenlet_hosts.keys()]

        # Any False = unignored error, so we stop everything here
        if False in results:
            logger.critical('Error in operation {}, exiting...'.format(', '.join(op_meta['names'])))
            break
