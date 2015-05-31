# pyinfra
# File: pyinfra/api/ssh.py
# Desc: handle all SSH related stuff

import time
from hashlib import sha1
from socket import error as socket_error, gaierror

from termcolor import colored
from paramiko import SSHClient, SFTPClient, RSAKey, MissingHostKeyPolicy, SSHException, AuthenticationException

import pyinfra
from pyinfra import config, logger


def _connect(hostname, **kwargs):
    '''Connect to a single host. Returns the hostname if succesful.'''
    try:
        # Create new client & connect to the host
        client = SSHClient()
        client.set_missing_host_key_policy(MissingHostKeyPolicy())
        client.connect(hostname, **kwargs)

        # Assign internally
        pyinfra._connections[hostname] = client
        logger.info('[{}] {}'.format(
            colored(hostname, attrs=['bold']),
            colored('Connected', 'green')
        ))

        return hostname
    except AuthenticationException as e:
        logger.critical('Auth error on: {}, {}'.format(hostname, e))
    except SSHException as e:
        logger.critical('SSH error on: {}, {}'.format(hostname, e))
    except socket_error as e:
        logger.critical('Could not connect: {}, {}'.format(hostname, e))
    except gaierror:
        logger.critical('Could not resolve: {}'.format(hostname))

def connect_all():
    '''Connect to all the configured servers in parallel.'''
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

    # Connect to each server in a thread
    outs = [
        pyinfra._pool.spawn(_connect, server, **kwargs)
        for server in config.SSH_HOSTS
    ]
    # Get the results
    connected_hosts = [out.get() for out in outs]

    # Assign working hosts to all hosts
    config.SSH_HOSTS = [host for host in connected_hosts if host is not None]


def run_shell_command(
    hostname, command,
    sudo=False, sudo_user=None, env=None, print_output=False, print_prefix=''
):
    '''Execute a command on the specified host.'''
    if env is None:
        env = {}

    logger.debug('Running command on {0}: "{1}"'.format(hostname, command))
    logger.debug('Command sudo?: {}, sudo user: {}, env: {}'.format(
        sudo, sudo_user, env
    ))

    # Use env & build our actual command
    env_string = ' '.join([
        '{}={}'.format(key, value)
        for key, value in env.iteritems()
    ])
    command = '{} {}'.format(env_string, command)

    # Escape "'s
    command = command.replace('"', '\\"')

    # No sudo, just bash wrap the command
    if not sudo:
        command = 'bash -c "{}"'.format(command)
    # Otherwise, work out sudo
    else:
        # Sudo with a user, then bash
        if sudo_user:
            command = 'sudo -u {} -S bash -c "{}"'.format(sudo_user, command)
        # Sudo then bash
        else:
            command = 'sudo -S bash -c "{}"'.format(command)

    if print_output:
        print '{}>>> {}'.format(print_prefix, command)

    # Get the connection for this hostname
    connection = pyinfra._connections[hostname]

    # Run it! Get stdout, stderr & the underlying channel
    _, stdout, stderr = connection.exec_command(command)
    return stdout.channel, stdout, stderr


def _get_sftp_connection(hostname):
    if hostname in pyinfra._sftp_connections:
        return pyinfra._sftp_connections[hostname]

    ssh_connection = pyinfra._connections[hostname]
    transport = ssh_connection.get_transport()
    client = SFTPClient.from_transport(transport)

    pyinfra._sftp_connections[hostname] = client

    return client

def _put_file(hostname, file_io, remote_location):
    sftp = _get_sftp_connection(hostname)
    sftp.putfo(file_io, remote_location)

def put_file(
    hostname, file_io, remote_file,
    sudo=False, sudo_user=None, print_output=False, print_prefix=''
):
    '''Upload/sync local/remote directories & files to the specified host.'''
    if not sudo:
        _put_file(hostname, file_io, remote_file)
    else:
        # sudo is a little more complicated, as you can only sftp with the SSH user connected
        # so upload to tmp and copy/chown w/sudo

        # Get temp file location
        hash_ = sha1()
        hash_.update(remote_file)
        hash_.update(str(time.time()))
        temp_file = '/tmp/{0}'.format(hash_.hexdigest())

        _put_file(hostname, file_io, temp_file)

        # Execute run_shell_command w/sudo to mv/chown it
        command = 'mv {0} {1} && chown {2}:{2} {1}'.format(
            temp_file, remote_file, sudo_user or 'root'
        )
        channel, _, stderr = run_shell_command(
            hostname, command,
            sudo=sudo, sudo_user=sudo_user,
            print_output=print_output,
            print_prefix=print_prefix
        )

        if channel.exit_status > 0:
            logger.critical('File error: {0}'.format(stderr))
            return False

    if print_output:
        print '{0} file uploaded: {1}'.format(print_prefix, remote_file)
