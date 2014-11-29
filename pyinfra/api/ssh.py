# pyinfra
# File: pyinfra/api/ssh.py
# Desc: handle all SSH related stuff

from gevent import sleep
from paramiko import RSAKey, SSHException
from pssh import (
    SSHClient,
    AuthenticationException, UnknownHostException, ConnectionErrorException, ProxyCommandException
)

import pyinfra
from pyinfra import config, logger


# Connect to all configured hosts
def connect_all():
    options = {
        'user': config.SSH_USER,
        'port': config.SSH_PORT,
        'retries': 0,
        'timeout': 3
    }

    # Password auth (boo!)
    if hasattr(config, 'SSH_PASS'):
        options['password'] = config.SSH_PASS
    else:
        options['pkey'] = RSAKey.from_private_key_file(
            filename=config.SSH_KEY,
            password=config.SSH_KEY_PASS
        )

    # New list to replace config list (removing non-connections)
    connected_servers = []
    def connect(server):
        try:
            pyinfra._connections[server] = SSHClient(server, **options)
            connected_servers.append(server)
            logger.info('Connected to {0}'.format(server))
        except AuthenticationException:
            logger.critical('Auth error on: {0}'.format(server))
        except UnknownHostException:
            logger.critical('Host not found: {0}'.format(server))
        except ConnectionErrorException:
            logger.critical('Could not connect to: {0}'.format(server))
        except ProxyCommandException:
            logger.critical('Proxy error on: {0}'.format(server))
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
    outs = [
        (server, pyinfra._pool.spawn(pyinfra._connections[server].exec_command, *args, **kwargs))
        for server in config.SSH_HOSTS
    ]

    # Join
    [out[1].join() for out in outs]
    # Get each data
    outs = [(out[0], out[1].get()) for out in outs]

    # Return the useful info
    return [(server, stdout, stderr) for (server, (_, _, stdout, stderr)) in outs]


def run_commands(server):
    commands = pyinfra._commands[server]
    connection = pyinfra._connections[server]

    # Loop through each command, execute it on the server
    for command in commands:
        print 'COMMAND', command['command']
        _, _, stdout, stderr = connection.exec_command(command['command'])
        sleep(.1)
        print 'STDOUT', stdout.read()
        print 'STDERR', stderr.read()


def run_all():
    outs = [
        pyinfra._pool.spawn(run_commands, server)
        for server in config.SSH_HOSTS
    ]
    # Wait until done
    [out.join() for out in outs]
