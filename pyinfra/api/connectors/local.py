# pyinfra
# File: pyinfra/api/local.py
# Desc: handle all local command related stuff

from __future__ import unicode_literals

import os

from socket import timeout as timeout_error
from subprocess import PIPE, Popen
from tempfile import mkstemp

import click
import gevent
import six

from pyinfra import logger
from pyinfra.api.util import get_file_io, make_command, read_buffer


def connect(state, host, for_fact=None):
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

    return True


def run_shell_command(
    state, host, command,
    get_pty=False, timeout=None, print_output=False,
    **command_kwargs
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

    command = make_command(command, **command_kwargs)

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
    state, host, filename_or_io, remote_filename,
    print_output=False,
    **command_kwargs
):
    _, temp_filename = mkstemp()

    # Load our file or IO object and write it to the temporary file
    with get_file_io(filename_or_io) as file_io:
        with open(temp_filename, 'wb') as temp_f:
            data = file_io.read()

            if isinstance(data, six.text_type):
                data = data.encode()

            temp_f.write(data)

    # Copy the file using `cp`
    status, _, stderr = run_shell_command(
        state, host, 'cp {0} {1}'.format(temp_filename, remote_filename),
        print_output=print_output,
        **command_kwargs
    )

    if temp_filename:
        os.remove(temp_filename)

    if not status:
        raise IOError('\n'.join(stderr))

    if print_output:
        print('{0}file copied: {1}'.format(host.print_prefix, remote_filename))

    return status
