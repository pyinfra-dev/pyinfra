# pyinfra
# File: pyinfra/api/ssh.py
# Desc: handle all SSH related stuff

from socket import error as socket_error, gaierror

from termcolor import colored
from paramiko import SSHClient, RSAKey, MissingHostKeyPolicy, SSHException, AuthenticationException

import pyinfra
from pyinfra import config, logger


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
    connected_hosts = []
    def connect(host):
        try:
            # Create new client & connect to the host
            client = SSHClient()
            client.set_missing_host_key_policy(MissingHostKeyPolicy())
            client.connect(host, **kwargs)

            # Assign internally
            pyinfra._connections[host] = client
            connected_hosts.append(host)
            logger.info('[{}] {}'.format(
                colored(host, attrs=['bold']),
                colored('Connected', 'green')
            ))
        except AuthenticationException as e:
            logger.critical('Auth error on: {}, {}'.format(host, e))
        except SSHException as e:
            logger.critical('SSH error on: {}, {}'.format(host, e))
        except socket_error as e:
            logger.critical('Could not connect: {}, {}'.format(host, e))
        except gaierror:
            logger.critical('Could not resolve: {}'.format(host))

    # Connect to each server in a thread
    outs = [
        pyinfra._pool.spawn(connect, server)
        for server in config.SSH_HOSTS
    ]
    # Wait until done
    [out.join() for out in outs]

    # Assign working hosts to all hosts
    config.SSH_HOSTS = connected_hosts


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
