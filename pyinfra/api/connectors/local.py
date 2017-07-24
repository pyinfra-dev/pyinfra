# pyinfra
# File: pyinfra/api/local.py
# Desc: handle all local command related stuff

from __future__ import unicode_literals

from socket import timeout as timeout_error
from subprocess import PIPE, Popen

import click
import gevent

from pyinfra import logger
from pyinfra.api.util import make_command, read_buffer


def connect(state, host, **kwargs):
    logger.info('{0}{1}'.format(
        host.print_prefix,
        click.style('Ready', 'green'),
    ))

    return True


def run_shell_command(
    state, host, command,
    sudo=False, sudo_user=None, su_user=None, preserve_sudo_env=False,
    get_pty=False, env=None, timeout=None, print_output=False,
):
    '''
    Execute a command on the local machine.

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

    logger.debug('--> Running command on localhost: {0}'.format(command))

    if print_output:
        print('{0}>>> {1}'.format(host.print_prefix, command))

    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)

    # Iterate through outputs to get an exit status and generate desired list
    # output, done in two greenlets so stdout isn't printed before stderr. Not
    # attached to state.pool to avoid blocking it with 2x n-hosts greenlets.
    stdout_reader = gevent.spawn(
        read_buffer, process.stdout,
        print_output=print_output,
        print_func=lambda line: '{0}{1}'.format(host.print_prefix, line),
    )
    stderr_reader = gevent.spawn(
        read_buffer, process.stderr,
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

    logger.debug('--> Waiting for exit status...')
    process.wait()

    # Close any open file descriptor
    process.stdout.close()

    logger.debug('--> Command exit status: {0}'.format(process.returncode))
    return process.returncode == 0, stdout, stderr


def put_file(
    state, host, file_io, remote_file,
    sudo=False, sudo_user=None, su_user=None, print_output=False,
):
    with open(remote_file, 'w') as f:
        f.write(file_io.read())

    if print_output:
        print('{0}file copied: {1}'.format(host.print_prefix, remote_file))
