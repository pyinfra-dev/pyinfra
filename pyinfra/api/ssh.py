# pyinfra
# File: pyinfra/api/ssh.py
# Desc: handle all SSH related stuff

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
        'timeout': 3
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


def run_ops(server):
    '''Runs a set of generated commands for a single targer server'''
    ops = pyinfra._ops[server]
    connection = pyinfra._connections[server]

    # For each op...
    for op in ops:
        commands = op['commands']
        # ...loop through each command, execute it on the server w/op-level preferences
        for i, command in enumerate(commands):
            logger.debug('Running command on {0}: "{1}"'.format(server, command))
            channel, _, stdout, stderr = connection.exec_command(command, sudo=op['sudo'])

            # Iterate the generators to get an exit status
            stdout = [line for line in stdout]
            stderr = [line for line in stderr]

            if channel.exit_status <= 0:
                pyinfra._results[server]['success_commands'] += 1
                logger.debug(stdout)
                logger.debug(stderr)
            else:
                pyinfra._results[server]['error_commands'] += 1

                if op['ignore_errors']:
                    logger.warning('IGNORED ERROR! {} {}'.format(stdout, stderr))
                else:
                    print 'COMMAND: {}'.format(command)
                    logger.critical('ERROR! {} {}'.format(stdout, stderr))
                    logger.critical('STOPPING {}'.format(server))
                    break

        # Op didn't break, so continue to the next one and ++success
        else:
            pyinfra._results[server]['success_ops'] += 1
            continue

        # Our op errored :(
        print "OP ERROR"
        pyinfra._results[server]['error_ops'] += 1


def run_all():
    '''Shortcut to run all commands on all servers each in a greenlet'''
    outs = [
        pyinfra._pool.spawn(run_ops, server)
        for server in config.SSH_HOSTS
    ]
    # Wait until done
    [out.join() for out in outs]

def run_serial():
    '''Shortcut to run all commands on all servers in serial'''
    for server in config.SSH_HOSTS:
        run_ops(server)
