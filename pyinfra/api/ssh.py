# pyinfra
# File: pyinfra/api/ssh.py
# Desc: handle all SSH related stuff

from __future__ import division, unicode_literals, print_function

from os import path
from time import sleep
from getpass import getpass
from socket import (
    gaierror,
    error as socket_error, timeout as timeout_error
)

import six
import gevent

from termcolor import colored
from paramiko.agent import AgentRequestHandler
from paramiko import (
    SSHClient, SFTPClient, RSAKey, MissingHostKeyPolicy,
    SSHException, AuthenticationException, PasswordRequiredException,
)

from pyinfra import logger
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.util import read_buffer, make_command, get_file_io


def _get_private_key(state, key_filename, key_password):
    if key_filename in state.private_keys:
        return state.private_keys[key_filename]

    ssh_key_filenames = [
        # Global from executed directory
        path.expanduser(key_filename)
    ]

    # Relative to the deploy
    if state.deploy_dir:
        ssh_key_filenames.append(
            path.join(state.deploy_dir, key_filename)
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
                            key_filename
                        )
                    )

            # API mode and no password? We can't continue!
                else:
                    raise PyinfraError(
                        'Private key file ({0}) is encrypted, set ssh_key_password to '
                        'use this key'.format(key_filename)
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
                        key_filename
                    )
                )

    # No break, so no key found
    else:
        raise IOError('No such private key file: {0}'.format(key_filename))

    state.private_keys[key_filename] = key
    return key


def connect(host, **kwargs):
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
            colored(name, attrs=['bold']),
            colored('Connected', 'green')
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
            name, kwargs.get('port', 22), e)
        )

    except EOFError as e:
        logger.error('EOF error connecting to {0}: {1}'.format(name, e))


def connect_all(state):
    '''
    Connect to all the configured servers in parallel. Reads/writes state.inventory.

    Args:
        state (``pyinfra.api.State`` obj): the state containing an inventory to connect to
    '''

    greenlets = {}

    for host in state.inventory:
        kwargs = {
            'username': host.data.ssh_user,
            'port': int(host.data.ssh_port) if host.data.ssh_port else 22,
            'timeout': state.config.TIMEOUT,
            # At this point we're assuming a password/key are provided
            'allow_agent': False,
            'look_for_keys': False
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

        greenlets[host.name] = state.pool.spawn(connect, host, **kwargs)

    gevent.wait(greenlets.values())

    # Get/set the results
    failed_hosts = set()
    connected_hosts = set()

    for name, greenlet in six.iteritems(greenlets):
        client = greenlet.get()

        if not client:
            failed_hosts.add(name)
        else:
            state.ssh_connections[name] = client
            connected_hosts.add(name)

    # Add connected hosts to inventory
    state.connected_hosts = connected_hosts

    # Add all the hosts as active
    state.active_hosts = set(greenlets.keys())

    # Remove those that failed, triggering FAIL_PERCENT check
    state.fail_hosts(failed_hosts)


def run_shell_command(
    state, hostname, command,
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

    print_prefix = '[{0}] '.format(colored(hostname, attrs=['bold']))

    if env is None:
        env = {}

    logger.debug('Building command on {0}: {1}'.format(hostname, command))

    debug_meta = {}

    for key, value in six.iteritems({
        'sudo': sudo, 'sudo_user': sudo_user, 'su_user': su_user, 'env': env
    }):
        if value:
            debug_meta[key] = value

    logger.debug('Command meta ({0})'.format(' '.join(
        '{0}: {1}'.format(key, value)
        for key, value in six.iteritems(debug_meta)
    )))

    command = make_command(command, env=env, sudo=sudo, sudo_user=sudo_user, su_user=su_user)

    logger.debug('--> Running command on {0}: {1}'.format(hostname, command))

    if print_output:
        print('{0}>>> {1}'.format(print_prefix, command))

    # Get the connection for this hostname
    connection = state.ssh_connections[hostname]

    # Run it! Get stdout, stderr & the underlying channel
    _, stdout_buffer, stderr_buffer = connection.exec_command(command, get_pty=get_pty)
    channel = stdout_buffer.channel

    # Iterate through outputs to get an exit status and generate desired list output,
    # done in two greenlets so stdout isn't printed before stderr. Not attached to
    # state.pool to avoid blocking it with 2x n-hosts greenlets.
    stdout_reader = gevent.spawn(
        read_buffer, stdout_buffer,
        print_output=print_output,
        print_func=lambda line: '{0}{1}'.format(print_prefix, line)
    )
    stderr_reader = gevent.spawn(
        read_buffer, stderr_buffer,
        print_output=print_output,
        print_func=lambda line: '{0}{1}'.format(print_prefix, colored(line, 'red'))
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

    # Wait until the exit code is ready. We have to sleep between checks to allow gevent
    # to jump to the paramiko networking stack to receive the final exit code. Normally
    # this is ready after reading out the buffers, but it's possible the exit code didn't
    # make it into the final read.
    ready = channel.exit_status_ready()
    while ready is False:
        logger.debug('--> Waiting for exit status...')
        sleep(0.001)
        ready = channel.exit_status_ready()

    logger.debug('--> Command exit status: {0}'.format(channel.exit_status))
    return channel, stdout, stderr


def _get_sftp_connection(state, hostname):
    # SFTP connections aren't *required* for deploys, so we create them on-demand
    if hostname in state.sftp_connections:
        return state.sftp_connections[hostname]

    ssh_connection = state.ssh_connections[hostname]
    transport = ssh_connection.get_transport()
    client = SFTPClient.from_transport(transport)

    state.sftp_connections[hostname] = client

    return client


def _put_file(state, hostname, filename_or_io, remote_location):
    with get_file_io(filename_or_io) as file_io:
        # Upload it via SFTP
        sftp = _get_sftp_connection(state, hostname)
        sftp.putfo(file_io, remote_location)


def put_file(
    state, hostname, file_io, remote_file,
    sudo=False, sudo_user=None, su_user=None, print_output=False
):
    '''
    Upload file-ios to the specified host using SFTP. Supports uploading files with sudo
    by uploading to a temporary directory then moving & chowning.
    '''

    print_prefix = '[{0}] '.format(colored(hostname, attrs=['bold']))

    # sudo/su are a little more complicated, as you can only sftp with the SSH user
    # connected,  so upload to tmp and copy/chown w/sudo and/or su_user
    if sudo or su_user:
        # Get temp file location
        temp_file = state.get_temp_filename(remote_file)
        _put_file(state, hostname, file_io, temp_file)

        # Execute run_shell_command w/sudo and/or su_user
        command = 'mv {0} {1}'.format(temp_file, remote_file)

        # Move it to the su_user if present
        if su_user:
            command = '{0} && chown {1} {2}'.format(command, su_user, remote_file)

        # Otherwise any sudo_user
        elif sudo_user:
            command = '{0} && chown {1} {2}'.format(command, sudo_user, remote_file)

        channel, _, stderr = run_shell_command(
            state, hostname, command,
            sudo=sudo, sudo_user=sudo_user, su_user=su_user,
            print_output=print_output
        )

        if channel.exit_status > 0:
            logger.error('File error: {0}'.format('\n'.join(stderr)))
            return False

    # No sudo and no su_user, so just upload it!
    else:
        _put_file(state, hostname, file_io, remote_file)

    if print_output:
        print('{0}file uploaded: {1}'.format(print_prefix, remote_file))
