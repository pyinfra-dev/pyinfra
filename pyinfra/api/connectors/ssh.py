from __future__ import print_function, unicode_literals

from distutils.spawn import find_executable
from getpass import getpass
from os import path
from socket import (
    error as socket_error,
    gaierror,
)

import click
import six

from paramiko import (
    AuthenticationException,
    DSSKey,
    ECDSAKey,
    Ed25519Key,
    MissingHostKeyPolicy,
    PasswordRequiredException,
    RSAKey,
    SFTPClient,
    SSHException,
)

import pyinfra

from pyinfra import logger
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.exceptions import ConnectError, PyinfraError
from pyinfra.api.util import get_file_io, memoize

from .sshuserclient import SSHClient
from .util import (
    get_sudo_password,
    make_unix_command,
    read_buffers_into_queue,
    run_local_process,
    split_combined_output,
    write_stdin,
)

EXECUTION_CONNECTOR = True


def make_names_data(hostname):
    yield '@ssh/{0}'.format(hostname), {'ssh_hostname': hostname}, []


def _raise_connect_error(host, message, data):
    message = '{0} ({1})'.format(message, data)
    raise ConnectError(message)


def _load_private_key_file(filename, key_filename, key_password):
    exception = PyinfraError('Invalid key: {0}'.format(filename))

    for key_cls in (RSAKey, DSSKey, ECDSAKey, Ed25519Key):
        try:
            return key_cls.from_private_key_file(
                filename=filename,
            )

        except PasswordRequiredException:
            if not key_password:
                # If password is not provided, but we're in CLI mode, ask for it. I'm not a
                # huge fan of having CLI specific code in here, but it doesn't really fit
                # anywhere else without duplicating lots of key related code into cli.py.
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

            try:
                return key_cls.from_private_key_file(
                    filename=filename,
                    password=key_password,
                )
            except SSHException as e:  # key does not match key_cls type
                exception = e
        except SSHException as e:  # key does not match key_cls type
            exception = e
    raise exception


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

    key = False
    key_file_exists = False

    for filename in ssh_key_filenames:
        if not path.isfile(filename):
            continue

        key_file_exists = True

        try:
            key = _load_private_key_file(filename, key_filename, key_password)
            break
        except SSHException:
            pass

    # No break, so no key found
    if not key:
        if not key_file_exists:
            raise PyinfraError('No such private key file: {0}'.format(key_filename))

        # TODO: upgrade min paramiko version to 2.7 and remove this (pyinfra v2)
        extra_info = ''
        from pkg_resources import get_distribution, parse_version
        if get_distribution('paramiko').parsed_version < parse_version('2.7'):
            extra_info = (
                '\n    Paramiko versions under 2.7 do not support the latest OpenSSH key formats,'
                ' upgrading may fix this error.'
                '\n    For more information, see this issue: '
                'https://github.com/Fizzadar/pyinfra/issues/548'
            )
        raise PyinfraError('Invalid private key file: {0}{1}'.format(key_filename, extra_info))

    # Load any certificate, names from OpenSSH:
    # https://github.com/openssh/openssh-portable/blob/049297de975b92adcc2db77e3fb7046c0e3c695d/ssh-keygen.c#L2453  # noqa: E501
    for certificate_filename in (
        '{0}-cert.pub'.format(key_filename),
        '{0}.pub'.format(key_filename),
    ):
        if path.isfile(certificate_filename):
            key.load_certificate(certificate_filename)

    state.private_keys[key_filename] = key
    return key


def _make_paramiko_kwargs(state, host):
    kwargs = {
        'allow_agent': False,
        'look_for_keys': False,
        'hostname': host.data.ssh_hostname or host.name,
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


def connect(state, host):
    '''
    Connect to a single host. Returns the SSH client if succesful. Stateless by
    design so can be run in parallel.
    '''

    kwargs = _make_paramiko_kwargs(state, host)
    logger.debug('Connecting to: {0} ({1})'.format(host.name, kwargs))

    hostname = kwargs.pop('hostname')

    try:
        # Create new client & connect to the host
        client = SSHClient()
        client.set_missing_host_key_policy(MissingHostKeyPolicy())
        client.connect(hostname, **kwargs)
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

        _raise_connect_error(host, 'Authentication error', auth_args)

    except SSHException as e:
        _raise_connect_error(host, 'SSH error', e)

    except gaierror:
        _raise_connect_error(host, 'Could not resolve hostname', hostname)

    except socket_error as e:
        _raise_connect_error(host, 'Could not connect', e)

    except EOFError as e:
        _raise_connect_error(host, 'EOF error', e)


def run_shell_command(
    state, host, command,
    get_pty=False,
    timeout=None,
    stdin=None,
    success_exit_codes=None,
    print_output=False,
    print_input=False,
    return_combined_output=False,
    use_sudo_password=False,
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
        env (dict): environment variables to set
        timeout (int): timeout for this command to complete before erroring

    Returns:
        tuple: (exit_code, stdout, stderr)
        stdout and stderr are both lists of strings from each buffer.
    '''

    if use_sudo_password:
        command_kwargs['use_sudo_password'] = get_sudo_password(
            state, host, use_sudo_password,
            run_shell_command=run_shell_command,
            put_file=put_file,
        )

    command = make_unix_command(command, state=state, **command_kwargs)
    actual_command = command.get_raw_value()

    logger.debug('Running command on {0}: (pty={1}) {2}'.format(
        host.name, get_pty, command,
    ))

    if print_input:
        click.echo('{0}>>> {1}'.format(host.print_prefix, command), err=True)

    # Run it! Get stdout, stderr & the underlying channel
    stdin_buffer, stdout_buffer, stderr_buffer = host.connection.exec_command(
        actual_command,
        get_pty=get_pty,
    )

    if stdin:
        write_stdin(stdin, stdin_buffer)

    combined_output = read_buffers_into_queue(
        stdout_buffer,
        stderr_buffer,
        timeout=timeout,
        print_output=print_output,
        print_prefix=host.print_prefix,
    )

    logger.debug('Waiting for exit status...')
    exit_status = stdout_buffer.channel.recv_exit_status()
    logger.debug('Command exit status: {0}'.format(exit_status))

    if success_exit_codes:
        status = exit_status in success_exit_codes
    else:
        status = exit_status == 0

    if return_combined_output:
        return status, combined_output

    stdout, stderr = split_combined_output(combined_output)
    return status, stdout, stderr


@memoize
def _get_sftp_connection(host):
    transport = host.connection.get_transport()

    try:
        return SFTPClient.from_transport(transport)
    except SSHException as e:
        six.raise_from(ConnectError((
            'Unable to establish SFTP connection. Check that the SFTP subsystem '
            'for the SSH service at {0} is enabled.'
        ).format(host)), e)


def _get_file(host, remote_filename, filename_or_io):
    with get_file_io(filename_or_io, 'wb') as file_io:
        sftp = _get_sftp_connection(host)
        sftp.getfo(remote_filename, file_io)


def get_file(
    state, host, remote_filename, filename_or_io,
    sudo=False, sudo_user=None, su_user=None,
    print_output=False, print_input=False,
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
            print_input=print_input,
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
                print_input=print_input,
                **command_kwargs
            )

        if remove_status is False:
            logger.error('File download remove temp error: {0}'.format('\n'.join(stderr)))
            return False

    else:
        _get_file(host, remote_filename, filename_or_io)

    if print_output:
        click.echo(
            '{0}file downloaded: {1}'.format(host.print_prefix, remote_filename),
            err=True,
        )

    return True


def _put_file(host, filename_or_io, remote_location):
    with get_file_io(filename_or_io) as file_io:
        sftp = _get_sftp_connection(host)
        sftp.putfo(file_io, remote_location)


def put_file(
    state, host, filename_or_io, remote_filename,
    sudo=False, sudo_user=None, su_user=None,
    print_output=False, print_input=False,
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
        command = StringCommand('mv', temp_file, QuoteString(remote_filename))

        # Move it to the su_user if present
        if su_user:
            command = StringCommand(command, '&&', 'chown', su_user, QuoteString(remote_filename))

        # Otherwise any sudo_user
        elif sudo_user:
            command = StringCommand(command, '&&', 'chown', sudo_user, QuoteString(remote_filename))

        status, _, stderr = run_shell_command(
            state, host, command,
            sudo=sudo, sudo_user=sudo_user, su_user=su_user,
            print_output=print_output,
            print_input=print_input,
            **command_kwargs
        )

        if status is False:
            logger.error('File upload error: {0}'.format('\n'.join(stderr)))
            return False

    # No sudo and no su_user, so just upload it!
    else:
        _put_file(host, filename_or_io, remote_filename)

    if print_output:
        click.echo(
            '{0}file uploaded: {1}'.format(host.print_prefix, remote_filename),
            err=True,
        )

    return True


def check_can_rsync(host):
    if host.data.ssh_key_password:
        raise NotImplementedError('Rsync does not currently work with SSH keys needing passwords.')

    if host.data.ssh_password:
        raise NotImplementedError('Rsync does not currently work with SSH passwords.')

    if not find_executable('rsync'):
        raise NotImplementedError('The `rsync` binary is not available on this system.')


def rsync(
    state, host, src, dest, flags,
    print_output=False, print_input=False,
    sudo=False,
    sudo_user=None,
    **ignored_kwargs
):
    hostname = host.data.ssh_hostname or host.name
    user = ''
    if host.data.ssh_user:
        user = '{0}@'.format(host.data.ssh_user)

    ssh_flags = []

    port = host.data.ssh_port
    if port:
        ssh_flags.append('-p {0}'.format(port))

    ssh_key = host.data.ssh_key
    if ssh_key:
        ssh_flags.append('-i {0}'.format(ssh_key))

    remote_rsync_command = 'rsync'
    if sudo:
        remote_rsync_command = 'sudo rsync'
        if sudo_user:
            remote_rsync_command = 'sudo -u {0} rsync'.format(sudo_user)

    rsync_command = (
        'rsync {rsync_flags} '
        "--rsh 'ssh -o BatchMode=yes -o StrictHostKeyChecking=no {ssh_flags}' "
        "--rsync-path '{remote_rsync_command}' "
        '{src} {user}{hostname}:{dest}'
    ).format(
        rsync_flags=' '.join(flags),
        ssh_flags=' '.join(ssh_flags),
        remote_rsync_command=remote_rsync_command,
        user=user, hostname=hostname,
        src=src, dest=dest,
    )

    if print_input:
        click.echo('{0}>>> {1}'.format(host.print_prefix, rsync_command), err=True)

    return_code, combined_output = run_local_process(
        rsync_command,
        print_output=print_output,
        print_prefix=host.print_prefix,
    )

    status = return_code == 0

    if not status:
        _, stderr = split_combined_output(combined_output)
        raise IOError('\n'.join(stderr))

    return True
