# pyinfra
# File: pyinfra/api/ssh.py
# Desc: handle all SSH related stuff

from termcolor import colored
from paramiko import RSAKey, SSHException
from pssh import (
    SSHClient,
    AuthenticationException, UnknownHostException, ConnectionErrorException
)

import pyinfra
from pyinfra import config, logger


# Connect to all configured hosts
def connect_all():
    '''Connect to all the configured servers'''
    kwargs = {
        'user': config.SSH_USER,
        'port': config.SSH_PORT,
        'num_retries': 0,
        'timeout': 10
    }

    # Password auth (boo!)
    if hasattr(config, 'SSH_PASS'):
        kwargs['password'] = config.SSH_PASS
    else:
        kwargs['pkey'] = RSAKey.from_private_key_file(
            filename=config.SSH_KEY,
            password=config.SSH_KEY_PASS
        )

    # New list to replace config list (removing non-connections)
    connected_servers = []
    def connect(server):
        try:
            pyinfra._connections[server] = SSHClient(server, **kwargs)
            connected_servers.append(server)
            logger.info('Connected to {0}'.format(server))
        except AuthenticationException:
            logger.critical('Auth error on: {0}'.format(server))
        except UnknownHostException:
            logger.critical('Host not found: {0}'.format(server))
        except ConnectionErrorException:
            logger.critical('Could not connect to: {0}'.format(server))
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


def run_all_command(*args, **kwargs):
    '''Runs a single command on all hosts in parallel, used for collecting facts'''
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
        channel,
        [line for line in stdout],
        [line for line in stderr]
    ) for (server, (channel, _, stdout, stderr)) in outs]

    if join_output is True:
        results = [
            (server, channel, '\n'.join(stdout), '\n'.join(stderr))
            for (server, channel, stdout, stderr) in results
        ]

    return results


def run_ops(server, print_output=False):
    '''Runs a set of generated commands for a single targer server'''
    logger.info('Starting operations on {}'.format(colored(server, attrs=['bold'])))

    ops = pyinfra._ops[server]
    connection = pyinfra._connections[server]

    # For each op...
    for op in ops:
        try:
            op_status = False
            commands = op['commands']
            # ...loop through each command, execute it on the server w/op-level preferences
            for i, command in enumerate(commands):
                logger.debug('Running command on {0}: "{1}"'.format(server, command))
                logger.debug('Command sudo?: {}, sudo user: {}, env: {}'.format(
                    op['sudo'], op['sudo_user'], op['env']
                ))

                # Use env & build our actual command
                env_string = ' '.join([
                    '{}={}'.format(key, value)
                    for key, value in op['env'].iteritems()
                ])
                command = '{} {}'.format(env_string, command)

                # Run it!
                channel, _, stdout, stderr = connection.exec_command(command,
                    sudo=op['sudo'], user=op['sudo_user']
                )

                # Iterate the generators to get an exit status
                stdout = [line for line in stdout]
                stderr = [line for line in stderr]

                if channel.exit_status <= 0:
                    pyinfra._results[server]['commands'] += 1
                else:
                    break

            # Op didn't break, so continue to the next one and ++success
            else:
                op_status = True

            # Op OK!
            if op_status is True:
                # Count success, log
                pyinfra._results[server]['ops'] += 1
                pyinfra._results[server]['success_ops'] += 1
                logger.info('{} on {}: {}'.format(
                    colored('Operation success', 'green'),
                    colored(server, attrs=['bold']),
                    op['name']
                ))

            # If the op failed somewhere
            else:
                # Count error, log
                pyinfra._results[server]['error_ops'] += 1
                logger.warning('Operation error on {}: {} (at command: {})'.format(
                    colored(server, attrs=['bold']),
                    op['name'], command
                ))

                # Break operation loop if not ignoring
                if op['ignore_errors']:
                    pyinfra._results[server]['ops'] += 1
                else:
                    break

        # Exception? always break operation loop
        except Exception as e:
            # Op broke so has errored :(
            pyinfra._results[server]['error_ops'] += 1
            logger.critical('Operation exception on {}: {} (at command: {}) {}'.format(server, op['name'], command, e))
            break

    # No ops broke, so all good!
    else:
        logger.info('Operations complete on {}'.format(colored(server, attrs=['bold'])))
        return

    logger.critical('Operations incomplete on {}'.format(colored(server, attrs=['bold'])))


def run_all(**kwargs):
    '''Shortcut to run all commands on all servers each in a greenlet'''
    outs = [
        pyinfra._pool.spawn(run_ops, server, **kwargs)
        for server in config.SSH_HOSTS
    ]
    # Wait until done
    [out.join() for out in outs]

def run_serial(**kwargs):
    '''Shortcut to run all commands on all servers in serial'''
    for server in config.SSH_HOSTS:
        run_ops(server, **kwargs)
