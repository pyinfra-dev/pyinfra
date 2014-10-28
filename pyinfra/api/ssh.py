# pyinfra
# File: pyinfra/api/ssh.py
# Desc: handle all SSH related stuff

from time import sleep
from threading import Thread

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
    servers = config.SSH_HOSTS
    threads = []
    while servers or threads:
        # Max 20 threads/connections at once
        while servers and len(threads) < 20:
            server = servers.pop()
            logger.debug('Connecting to {0}'.format(server))
            thread = Thread(target=connect, args=(server,))
            thread.start()
            threads.append(thread)

        # Attempt to join threads
        [t.join(0.001) for t in threads]
        # Weed out the complete threads
        threads = [t for t in threads if t is not None and t.isAlive()]
        sleep(1)

    config.SSH_HOSTS = connected_servers


def run_command(*args, **kwargs):
    outs = [
        (server, pyinfra._pool.spawn(pyinfra._connections[server].exec_command, *args, **kwargs))
        for server in config.SSH_HOSTS
    ]

    # Join
    [out[1].join() for out in outs]
    # Get each data
    outs = [(out[0], out[1].get()) for out in outs]

    # Process & assign each fact
    return [(server, stdout, stderr) for (server, (_, _, stdout, stderr)) in outs]


def run_commands(commands):
    pass

def run_all():
    for host in config.SSH_HOSTS:
        print host
