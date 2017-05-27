# pyinfra
# File: pyinfra/api/ssh.py
# Desc: handle all SSH related stuff

from __future__ import print_function, unicode_literals

from socket import (
    error as socket_error,
    gaierror,
    timeout as timeout_error,
)

import click
import gevent
import six

from paramiko import (
    AuthenticationException,
    MissingHostKeyPolicy,
    SFTPClient,
    SSHClient,
    SSHException,
)
from paramiko.agent import AgentRequestHandler

from pyinfra import logger
from pyinfra.api.util import get_file_io, make_command, read_buffer

SFTP_CONNECTIONS = {}


def connect(state, host, **kwargs):
    '''
    Connect to a single host. Returns the SSH client if succesful. Stateless by design so
    can be run in parallel.
    '''

    logger.debug('Connecting to: {0} ({1})'.format(host.name, kwargs))

    name = host.name
    hostname = host.data.ssh_hostname or name

    try:
        # Create new client & connect to the host
        client = SSHClient()
        client.set_missing_host_key_policy(MissingHostKeyPolicy())
        client.connect(hostname, **kwargs)

        # Enable SSH forwarding
        session = client.get_transport().open_session()
        AgentRequestHandler(session)

        # Log
        logger.info('[{0}] {1}'.format(
            click.style(name, bold=True),
            click.style('Connected', 'green'),
        ))

        return client

    except AuthenticationException as e:
        logger.error('Auth error on: {0}, {1}'.format(name, e))

    except SSHException as e:
        logger.error('SSH error on: {0}, {1}'.format(name, e))

    except gaierror:
        if hostname == name:
            logger.error('Could not resolve {0}'.format(name))
        else:
            logger.error('Could not resolve for {0} (SSH host: {1})'.format(name, hostname))

    except socket_error as e:
        logger.error('Could not connect: {0}:{1}, {2}'.format(
            name, kwargs.get('port', 22), e),
        )

    except EOFError as e:
        logger.error('EOF error connecting to {0}: {1}'.format(name, e))


def run_shell_command(
    state, host, command,
    sudo=False, sudo_user=None, su_user=None,
    get_pty=False, env=None, timeout=None, print_output=False,
):
    '''
    Execute a command on the specified host.

    Args:
        state (``pyinfra.api.State`` obj): state object for this command
        hostname (string): hostname of the target
        command (string): actual command to execute
        sudo (boolean): whether to wrap the command with sudo
        sudo_user (string): user to sudo to
        get_pty (boolean): whether to get a PTY before executing the command
        env (dict): envrionment variables to set
        timeout (int): timeout for this command to complete before erroring

    Returns:
        tuple: (channel, stdout, stderr)

        Channel is a Paramiko channel object, mainly used for it's ``.exit_code`` attribute.

        stdout and stderr are both lists of strings from each buffer.
    '''

    print_prefix = host.print_prefix

    if env is None:
        env = {}

    logger.debug('Building command on {0}: {1}'.format(host.name, command))

    debug_meta = {}

    for key, value in (
        ('sudo', sudo),
        ('sudo_user', sudo_user),
        ('su_user', su_user),
        ('env', env),
    ):
        if value:
            debug_meta[key] = value

    logger.debug('Command meta ({0})'.format(' '.join(
        '{0}: {1}'.format(key, value)
        for key, value in six.iteritems(debug_meta)
    )))

    command = make_command(command, env=env, sudo=sudo, sudo_user=sudo_user, su_user=su_user)

    logger.debug('--> Running command on {0}: {1}'.format(host.name, command))

    if print_output:
        print('{0}>>> {1}'.format(print_prefix, command))

    # Run it! Get stdout, stderr & the underlying channel
    _, stdout_buffer, stderr_buffer = host.connection.exec_command(command, get_pty=get_pty)
    channel = stdout_buffer.channel

    # Iterate through outputs to get an exit status and generate desired list output,
    # done in two greenlets so stdout isn't printed before stderr. Not attached to
    # state.pool to avoid blocking it with 2x n-hosts greenlets.
    stdout_reader = gevent.spawn(
        read_buffer, stdout_buffer,
        print_output=print_output,
        print_func=lambda line: '{0}{1}'.format(print_prefix, line),
    )
    stderr_reader = gevent.spawn(
        read_buffer, stderr_buffer,
        print_output=print_output,
        print_func=lambda line: '{0}{1}'.format(print_prefix, click.style(line, 'red')),
    )

    # Wait on output, with our timeout (or None)
    greenlets = gevent.wait((stdout_reader, stderr_reader), timeout=timeout)

    # Timeout doesn't raise an exception, but gevent.wait returns the greenlets which did
    # complete. So if both haven't completed, we kill them and fail with a timeout.
    if len(greenlets) != 2:
        stdout_reader.kill()
        stderr_reader.kill()
        raise timeout_error()

    # Read the buffers into a list of lines
    stdout = stdout_reader.get()
    stderr = stderr_reader.get()

    logger.debug('--> Waiting for exit status...')
    exit_status = channel.recv_exit_status()

    logger.debug('--> Command exit status: {0}'.format(exit_status))
    return exit_status == 0, stdout, stderr


def _get_sftp_connection(host):
    # SFTP connections aren't *required* for deploys, so we create them on-demand
    if host in SFTP_CONNECTIONS:
        return SFTP_CONNECTIONS[host]

    transport = host.connection.get_transport()
    client = SFTPClient.from_transport(transport)

    SFTP_CONNECTIONS[host] = client

    return client


def _put_file(host, filename_or_io, remote_location):
    with get_file_io(filename_or_io) as file_io:
        # Upload it via SFTP
        sftp = _get_sftp_connection(host)
        sftp.putfo(file_io, remote_location)


def put_file(
    state, host, file_io, remote_file,
    sudo=False, sudo_user=None, su_user=None, print_output=False,
):
    '''
    Upload file-ios to the specified host using SFTP. Supports uploading files with sudo
    by uploading to a temporary directory then moving & chowning.
    '''

    print_prefix = '[{0}] '.format(click.style(host.name, bold=True))

    # sudo/su are a little more complicated, as you can only sftp with the SSH user
    # connected,  so upload to tmp and copy/chown w/sudo and/or su_user
    if sudo or su_user:
        # Get temp file location
        temp_file = state.get_temp_filename(remote_file)
        _put_file(host, file_io, temp_file)

        # Execute run_shell_command w/sudo and/or su_user
        command = 'mv {0} {1}'.format(temp_file, remote_file)

        # Move it to the su_user if present
        if su_user:
            command = '{0} && chown {1} {2}'.format(command, su_user, remote_file)

        # Otherwise any sudo_user
        elif sudo_user:
            command = '{0} && chown {1} {2}'.format(command, sudo_user, remote_file)

        status, _, stderr = run_shell_command(
            state, host, command,
            sudo=sudo, sudo_user=sudo_user, su_user=su_user,
            print_output=print_output,
        )

        if not status:
            logger.error('File error: {0}'.format('\n'.join(stderr)))
            return False

    # No sudo and no su_user, so just upload it!
    else:
        _put_file(host, file_io, remote_file)

    if print_output:
        print('{0}file uploaded: {1}'.format(print_prefix, remote_file))
