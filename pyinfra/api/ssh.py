# pyinfra
# File: pyinfra/api/ssh.py
# Desc: handle all SSH related stuff

from termcolor import colored
from paramiko import SSHClient, RSAKey, MissingHostKeyPolicy, SSHException, AuthenticationException

import pyinfra
from pyinfra import config, logger


def run_all_command(*args, **kwargs):
    '''Runs a single command on all hosts in parallel, used for collecting facts.'''
    join_output = kwargs.pop('join_output', False)

    outs = [
        (server, pyinfra._pool.spawn(pyinfra._connections[server].exec_command, *args, **kwargs))
        for server in config.SSH_HOSTS
    ]

    # Join
    [out[1].join() for out in outs]
    # Get each data
    outs = [(out[0], out[1].get()) for out in outs]

    # Return the useful info
    results = [(
        server,
        [line.strip() for line in stdout],
        [line.strip() for line in stderr]
    ) for (server, (_, stdout, stderr)) in outs]

    if join_output is True:
        results = [
            (server, '\n'.join(stdout), '\n'.join(stderr))
            for (server, stdout, stderr) in results
        ]

    return results


def connect_all():
    '''Connect to all the configured servers.'''
    kwargs = {
        'username': config.SSH_USER,
        'port': getattr(config, 'SSH_PORT', 22),
        'timeout': 10
    }

    # Password auth (boo!)
    if hasattr(config, 'SSH_PASS'):
        kwargs['password'] = config.SSH_PASS
    else:
        kwargs['pkey'] = RSAKey.from_private_key_file(
            filename=config.SSH_KEY,
            password=getattr(config, 'SSH_KEY_PASS', None)
        )

    # New list to replace config list (removing non-connections)
    connected_servers = []
    def connect(server):
        try:
            # Create new client & connect to the host
            client = SSHClient()
            client.set_missing_host_key_policy(MissingHostKeyPolicy())
            client.connect(server, **kwargs)

            # Assign internally
            pyinfra._connections[server] = client
            connected_servers.append(server)
            logger.info('[{}] {}'.format(
                colored(server, attrs=['bold']),
                colored('Connected', 'green')
            ))
        except AuthenticationException:
            logger.critical('Auth error on: {0}'.format(server))
        except SSHException as e:
            logger.critical('SSH error on: {0}, {1}'.format(server, e))

    # Connect to each server in a thread
    outs = [
        pyinfra._pool.spawn(connect, server)
        for server in config.SSH_HOSTS
    ]
    # Wait until done
    [out.join() for out in outs]

    # Assign working hosts to all hosts
    config.SSH_HOSTS = connected_servers


def run_op(hostname, op_hash, print_output=False):
    '''Runs a single operation on a remote server.'''
    ops = pyinfra._ops[hostname]

    if op_hash not in ops:
        logger.debug('(Skipping) no op {} on {}'.format(op_hash, hostname))
        return

    connection = pyinfra._connections[hostname]
    commands = pyinfra._ops[hostname][op_hash]
    op_meta = pyinfra._op_meta[op_hash]

    logger.debug('Starting operation {} on {}'.format(', '.join(op_meta['names']), hostname))
    # ...loop through each command, execute it on the server w/op-level preferences
    for i, command in enumerate(commands):
        logger.debug('Running command on {0}: "{1}"'.format(hostname, command))
        logger.debug('Command sudo?: {}, sudo user: {}, env: {}'.format(
            op_meta['sudo'], op_meta['sudo_user'], op_meta['env']
        ))

        # Use env & build our actual command
        env_string = ' '.join([
            '{}={}'.format(key, value)
            for key, value in op_meta['env'].iteritems()
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

        print_prefix = '[{}] '.format(colored(hostname, attrs=['bold']))
        if print_output:
            print '{}>>> {}'.format(print_prefix, command)

        # Run it! Get stdout, stderr & the underlying channel
        _, stdout, stderr = connection.exec_command(command)
        channel = stdout.channel

        # Iterate through outputs to get an exit status
        # this iterates as the socket data comes in, which gevent patches
        for line in stdout:
            if print_output:
                print '{}{}'.format(print_prefix, line.strip())
        for line in stderr:
            if print_output:
                print '{}{}'.format(print_prefix, line.strip())

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
            colored('Success' if len(commands) > 0 else 'No changes', 'green')
        ))

        return True

    # If the op failed somewhere
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

    # Unignored failure => False
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
            logger.critical('Error in operation {} on {}, exiting...'.format(', '.join(op_meta['names']), hostname))
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
