# pyinfra
# File: pyinfra/api/ssh.py
# Desc: handle all SSH related stuff

from __future__ import print_function, unicode_literals

from getpass import getpass
from os import path
from socket import (
    error as socket_error,
    gaierror,
    timeout as timeout_error,
)

import click
import gevent

from paramiko import (
    AuthenticationException,
    MissingHostKeyPolicy,
    PasswordRequiredException,
    RSAKey,
    SFTPClient,
    SSHClient,
    SSHConfig,
    SSHException,
)
from paramiko.agent import AgentRequestHandler

from pyinfra import logger
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.util import get_file_io, make_command, read_buffer

SFTP_CONNECTIONS = {}


def _log_connect_error(host, message, data):
    logger.error('{0}{1} ({2})'.format(
        host.print_prefix,
        click.style(message, 'red'),
        data,
    ))


def _get_private_key(state, key_filename, key_password):
    if key_filename in state.private_keys:
        return state.private_keys[key_filename]

    ssh_key_filenames = [
        # Global from executed directory
        path.expanduser(key_filename),
    ]

    # Relative to the deploy
    if state.deploy_dir:
        ssh_key_filenames.append(
            path.join(state.deploy_dir, key_filename),
        )

    for filename in ssh_key_filenames:
        if not path.isfile(filename):
            continue

        # First, lets try the key without a password
        try:
            key = RSAKey.from_private_key_file(
                filename=filename,
            )
            break

        # Key is encrypted!
        except PasswordRequiredException:
            # If password is not provided, but we're in CLI mode, ask for it. I'm not a
            # huge fan of having CLI specific code in here, but it doesn't really fit
            # anywhere else without duplicating lots of key related code into cli.py.
            if not key_password:
                if state.is_cli:
                    key_password = getpass(
                        'Enter password for private key: {0}: '.format(
                            key_filename,
                        ),
                    )

            # API mode and no password? We can't continue!
                else:
                    raise PyinfraError(
                        'Private key file ({0}) is encrypted, set ssh_key_password to '
                        'use this key'.format(key_filename),
                    )

            # Now, try opening the key with the password
            try:
                key = RSAKey.from_private_key_file(
                    filename=filename,
                    password=key_password,
                )
                break

            except SSHException:
                raise PyinfraError(
                    'Incorrect password for private key: {0}'.format(
                        key_filename,
                    ),
                )

    # No break, so no key found
    else:
        raise IOError('No such private key file: {0}'.format(key_filename))

    state.private_keys[key_filename] = key
    return key


def get_ssh_config(host):
    ssh_config = SSHConfig()
    user_config_file = path.expanduser("~/.ssh/config")
    if path.exists(user_config_file):
        cfg = dict()

        with open(user_config_file) as f:
            ssh_config.parse(f)
            host_config = ssh_config.lookup(host)
            if "user" in host_config:
                cfg["username"] = host_config["user"]

            if "proxycommand" in host_config:
                cfg["sock"] = ProxyCommand(host_config["proxycommand"])

            if "identityfile" in host_config:
                cfg['key_filename'] = host_config['identityfile']

            if "port" in host_config:
                cfg["port"] = int(host_config["port"])

            return cfg


def _make_paramiko_kwargs(state, host):
    kwargs = {
        'username': host.data.ssh_user,
        'port': int(host.data.ssh_port) if host.data.ssh_port else 22,
        'timeout': state.config.TIMEOUT,
        # At this point we're assuming a password/key are provided
        'allow_agent': False,
        'look_for_keys': False,
    }

    # Password auth (boo!)
    if host.data.ssh_password:
        kwargs['password'] = host.data.ssh_password

    # Key auth!
    elif host.data.ssh_key:
        kwargs['pkey'] = _get_private_key(
            state,
            key_filename=host.data.ssh_key,
            key_password=host.data.ssh_key_password,
        )

    # No key or password, so let's have paramiko look for SSH agents and user keys
    else:
        kwargs['allow_agent'] = True
        kwargs['look_for_keys'] = True
        kwargs.update(get_ssh_config(host.name))

    return kwargs


def connect(state, host, for_fact=None):
    '''
    Connect to a single host. Returns the SSH client if succesful. Stateless by
    design so can be run in parallel.
    '''

    kwargs = _make_paramiko_kwargs(state, host)
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
        log_message = '{0}{1}'.format(
            host.print_prefix,
            click.style('Connected', 'green'),
        )

        if for_fact:
            log_message = '{0}{1}'.format(
                log_message,
                ' (for {0} fact)'.format(for_fact),
            )

        logger.info(log_message)

        return client

    except AuthenticationException as e:
        auth_kwargs = {}

        for key, value in kwargs.items():
            if key in ('username', 'password'):
                auth_kwargs[key] = value
                continue

            if key == 'pkey' and value:
                auth_kwargs['key'] = host.data.ssh_key

        auth_args = ', '.join(
            '{0}={1}'.format(key, value)
            for key, value in auth_kwargs.items()
        )

        _log_connect_error(host, 'Authentication error', auth_args)

    except SSHException as e:
        _log_connect_error(host, 'SSH error', e)

    except gaierror:
        _log_connect_error(host, 'Could not resolve hostname', hostname)

    except socket_error as e:
        _log_connect_error(host, 'Could not connect', e)

    except EOFError as e:
        _log_connect_error(host, 'EOF error', e)


def run_shell_command(
    state, host, command,
    sudo=False, sudo_user=None, su_user=None, preserve_sudo_env=False,
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
        tuple: (exit_code, stdout, stderr)
        stdout and stderr are both lists of strings from each buffer.
    '''

    command = make_command(
        command,
        env=env,
        sudo=sudo,
        sudo_user=sudo_user,
        su_user=su_user,
        preserve_sudo_env=preserve_sudo_env,
    )

    logger.debug('Running command on {0}: {1}'.format(host.name, command))

    if print_output:
        print('{0}>>> {1}'.format(host.print_prefix, command))

    # Run it! Get stdout, stderr & the underlying channel
    _, stdout_buffer, stderr_buffer = host.connection.exec_command(
        command,
        get_pty=get_pty,
    )

    channel = stdout_buffer.channel

    # Iterate through outputs to get an exit status and generate desired list
    # output, done in two greenlets so stdout isn't printed before stderr. Not
    # attached to state.pool to avoid blocking it with 2x n-hosts greenlets.
    stdout_reader = gevent.spawn(
        read_buffer, stdout_buffer,
        print_output=print_output,
        print_func=lambda line: '{0}{1}'.format(host.print_prefix, line),
    )
    stderr_reader = gevent.spawn(
        read_buffer, stderr_buffer,
        print_output=print_output,
        print_func=lambda line: '{0}{1}'.format(
            host.print_prefix, click.style(line, 'red'),
        ),
    )

    # Wait on output, with our timeout (or None)
    greenlets = gevent.wait((stdout_reader, stderr_reader), timeout=timeout)

    # Timeout doesn't raise an exception, but gevent.wait returns the greenlets
    # which did complete. So if both haven't completed, we kill them and fail
    # with a timeout.
    if len(greenlets) != 2:
        stdout_reader.kill()
        stderr_reader.kill()

        raise timeout_error()

    # Read the buffers into a list of lines
    stdout = stdout_reader.get()
    stderr = stderr_reader.get()

    logger.debug('Waiting for exit status...')
    exit_status = channel.recv_exit_status()

    logger.debug('Command exit status: {0}'.format(exit_status))
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

        try:
            sftp.putfo(file_io, remote_location)

        except IOError as e:
            # IO mismatch errors might indicate full disks
            if e.message.startswith('size mismatch in put!  0 !='):
                raise IOError('{0} (disk may be full)'.format(e.message))

            raise


def put_file(
    state, host, filename_or_io, remote_file,
    sudo=False, sudo_user=None, su_user=None, print_output=False,
):
    '''
    Upload file-ios to the specified host using SFTP. Supports uploading files
    with sudo by uploading to a temporary directory then moving & chowning.
    '''

    # sudo/su are a little more complicated, as you can only sftp with the SSH
    # user connected, so upload to tmp and copy/chown w/sudo and/or su_user
    if sudo or su_user:
        # Get temp file location
        temp_file = state.get_temp_filename(remote_file)
        _put_file(host, filename_or_io, temp_file)

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

        if status is False:
            logger.error('File error: {0}'.format('\n'.join(stderr)))
            return False

    # No sudo and no su_user, so just upload it!
    else:
        _put_file(host, filename_or_io, remote_file)

    if print_output:
        print('{0}file uploaded: {1}'.format(host.print_prefix, remote_file))
