from getpass import getpass
from os import path
from socket import (
    error as socket_error,
    gaierror,
)

import click

from paramiko import (
    AuthenticationException,
    MissingHostKeyPolicy,
    PasswordRequiredException,
    RSAKey,
    SFTPClient,
    SSHException,
)
from paramiko.agent import AgentRequestHandler

import pyinfra

from pyinfra import logger
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.util import get_file_io, make_command, memoize

from .sshuserclient import SSHClient
from .util import read_buffers_into_queue, split_combined_output


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
                if pyinfra.is_cli:
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


def _make_paramiko_kwargs(state, host):
    kwargs = {
        'allow_agent': False,
        'look_for_keys': False,
    }

    for key, value in (
        ('username', host.data.ssh_user),
        ('port', int(host.data.ssh_port or 0)),
        ('timeout', state.config.CONNECT_TIMEOUT),
    ):
        if value:
            kwargs[key] = value

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

    return kwargs


def connect(state, host, for_fact=None):
    '''
    Connect to a single host. Returns the SSH client if succesful. Stateless by
    design so can be run in parallel.
    '''

    kwargs = _make_paramiko_kwargs(state, host)
    logger.debug('Connecting to: {0} ({1})'.format(host.name, kwargs))

    # Hostname can be provided via SSH config (alias), data, or the hosts name
    hostname = kwargs.pop(
        'hostname',
        host.data.ssh_hostname or host.name,
    )

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

    except AuthenticationException:
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
    get_pty=False, timeout=None, print_output=False,
    return_combined_output=False,
    **command_kwargs
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

    command = make_command(command, **command_kwargs)

    logger.debug('Running command on {0}: (pty={1}) {2}'.format(
        host.name, get_pty, command,
    ))

    if print_output:
        print('{0}>>> {1}'.format(host.print_prefix, command))

    # Run it! Get stdout, stderr & the underlying channel
    _, stdout_buffer, stderr_buffer = host.connection.exec_command(
        command,
        get_pty=get_pty,
    )

    combined_output = read_buffers_into_queue(
        host,
        stdout_buffer,
        stderr_buffer,
        timeout=timeout,
        print_output=print_output,
    )

    logger.debug('Waiting for exit status...')
    exit_status = stdout_buffer.channel.recv_exit_status()
    logger.debug('Command exit status: {0}'.format(exit_status))

    status = exit_status == 0

    if return_combined_output:
        return status, combined_output

    stdout, stderr = split_combined_output(combined_output)
    return status, stdout, stderr


@memoize
def _get_sftp_connection(host):
    transport = host.connection.get_transport()
    return SFTPClient.from_transport(transport)


def _get_file(host, remote_filename, filename_or_io):
    with get_file_io(filename_or_io, 'wb') as file_io:
        sftp = _get_sftp_connection(host)
        sftp.getfo(remote_filename, file_io)


def get_file(
    state, host, remote_filename, filename_or_io,
    sudo=False, sudo_user=None, su_user=None, print_output=False,
    **command_kwargs
):
    '''
    Download a file from the remote host using SFTP. Supports download files
    with sudo by copying to a temporary directory with read permissions,
    downloading and then removing the copy.
    '''

    if sudo or su_user:
        # Get temp file location
        temp_file = state.get_temp_filename(remote_filename)

        # Copy the file to the tempfile location and add read permissions
        command = 'cp {0} {1} && chmod +r {0}'.format(remote_filename, temp_file)

        copy_status, _, stderr = run_shell_command(
            state, host, command,
            sudo=sudo, sudo_user=sudo_user, su_user=su_user,
            print_output=print_output,
            **command_kwargs
        )

        if copy_status is False:
            logger.error('File download copy temp error: {0}'.format('\n'.join(stderr)))
            return False

        try:
            _get_file(host, temp_file, filename_or_io)

        # Ensure that, even if we encounter an error, we (attempt to) remove the
        # temporary copy of the file.
        finally:
            remove_status, _, stderr = run_shell_command(
                state, host, 'rm -f {0}'.format(temp_file),
                sudo=sudo, sudo_user=sudo_user, su_user=su_user,
                print_output=print_output,
                **command_kwargs
            )

        if remove_status is False:
            logger.error('File download remove temp error: {0}'.format('\n'.join(stderr)))
            return False

    else:
        _get_file(host, remote_filename, filename_or_io)

    if print_output:
        print('{0}file downloaded: {1}'.format(host.print_prefix, remote_filename))

    return True


def _put_file(host, filename_or_io, remote_location):
    with get_file_io(filename_or_io) as file_io:
        # Upload it via SFTP
        sftp = _get_sftp_connection(host)

        try:
            sftp.putfo(file_io, remote_location)
        except IOError as e:
            # IO mismatch errors might indicate full disks
            message = getattr(e, 'message', None)
            if message and message.startswith('size mismatch in put!  0 !='):
                raise IOError('{0} (disk may be full)'.format(e.message))

            raise


def put_file(
    state, host, filename_or_io, remote_filename,
    sudo=False, sudo_user=None, su_user=None, print_output=False,
    **command_kwargs
):
    '''
    Upload file-ios to the specified host using SFTP. Supports uploading files
    with sudo by uploading to a temporary directory then moving & chowning.
    '''

    # sudo/su are a little more complicated, as you can only sftp with the SSH
    # user connected, so upload to tmp and copy/chown w/sudo and/or su_user
    if sudo or su_user:
        # Get temp file location
        temp_file = state.get_temp_filename(remote_filename)
        _put_file(host, filename_or_io, temp_file)

        # Execute run_shell_command w/sudo and/or su_user
        command = 'mv {0} {1}'.format(temp_file, remote_filename)

        # Move it to the su_user if present
        if su_user:
            command = '{0} && chown {1} {2}'.format(command, su_user, remote_filename)

        # Otherwise any sudo_user
        elif sudo_user:
            command = '{0} && chown {1} {2}'.format(command, sudo_user, remote_filename)

        status, _, stderr = run_shell_command(
            state, host, command,
            sudo=sudo, sudo_user=sudo_user, su_user=su_user,
            print_output=print_output,
            **command_kwargs
        )

        if status is False:
            logger.error('File upload error: {0}'.format('\n'.join(stderr)))
            return False

    # No sudo and no su_user, so just upload it!
    else:
        _put_file(host, filename_or_io, remote_filename)

    if print_output:
        print('{0}file uploaded: {1}'.format(host.print_prefix, remote_filename))

    return True
