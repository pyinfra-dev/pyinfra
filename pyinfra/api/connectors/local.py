from __future__ import unicode_literals

import os

from distutils.spawn import find_executable
from tempfile import mkstemp

import click
import six

from pyinfra import logger
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import get_file_io

from .util import (
    get_sudo_password,
    make_unix_command,
    run_local_process,
    split_combined_output,
)

EXECUTION_CONNECTOR = True


def make_names_data(hostname=None):
    if hostname is not None:
        raise InventoryError('Cannot have more than one @local')

    yield '@local', {}, ['@local']


def connect(state, host):
    return True


def run_shell_command(
    state, host, command,
    get_pty=False,  # ignored
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
    Execute a command on the local machine.

    Args:
        state (``pyinfra.api.State`` object): state object for this command
        host (``pyinfra.api.Host`` object): the target host
        command (string): actual command to execute
        sudo (boolean): whether to wrap the command with sudo
        sudo_user (string): user to sudo to
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

    logger.debug('--> Running command on localhost: {0}'.format(command))

    if print_input:
        click.echo('{0}>>> {1}'.format(host.print_prefix, command), err=True)

    return_code, combined_output = run_local_process(
        actual_command,
        stdin=stdin,
        timeout=timeout,
        print_output=print_output,
        print_prefix=host.print_prefix,
    )

    if success_exit_codes:
        status = return_code in success_exit_codes
    else:
        status = return_code == 0

    if return_combined_output:
        return status, combined_output

    stdout, stderr = split_combined_output(combined_output)
    return status, stdout, stderr


def put_file(
    state, host, filename_or_io, remote_filename,
    print_output=False, print_input=False,
    **command_kwargs
):
    '''
    Upload a local file or IO object by copying it to a temporary directory
    and then writing it to the upload location.
    '''

    _, temp_filename = mkstemp()

    try:
        # Load our file or IO object and write it to the temporary file
        with get_file_io(filename_or_io) as file_io:
            with open(temp_filename, 'wb') as temp_f:
                data = file_io.read()

                if isinstance(data, six.text_type):
                    data = data.encode()

                temp_f.write(data)

        # Copy the file using `cp` such that we support sudo/su
        status, _, stderr = run_shell_command(
            state, host, 'cp {0} {1}'.format(temp_filename, remote_filename),
            print_output=print_output,
            print_input=print_input,
            **command_kwargs
        )

        if not status:
            raise IOError('\n'.join(stderr))
    finally:
        os.remove(temp_filename)

    if print_output:
        click.echo(
            '{0}file copied: {1}'.format(host.print_prefix, remote_filename),
            err=True,
        )

    return status


def get_file(
    state, host, remote_filename, filename_or_io,
    print_output=False, print_input=False,
    **command_kwargs
):
    '''
    Download a local file by copying it to a temporary location and then writing
    it to our filename or IO object.
    '''

    _, temp_filename = mkstemp()

    try:
        # Copy the file using `cp` such that we support sudo/su
        status, _, stderr = run_shell_command(
            state, host, 'cp {0} {1}'.format(remote_filename, temp_filename),
            print_output=print_output,
            print_input=print_input,
            **command_kwargs
        )

        if not status:
            raise IOError('\n'.join(stderr))

        # Load our file or IO object and write it to the temporary file
        with open(temp_filename) as temp_f:
            with get_file_io(filename_or_io, 'wb') as file_io:
                data = temp_f.read()

                if isinstance(data, six.text_type):
                    data = data.encode()

                file_io.write(data)
    finally:
        os.remove(temp_filename)

    if print_output:
        click.echo(
            '{0}file copied: {1}'.format(host.print_prefix, remote_filename),
            err=True,
        )

    return True


def check_can_rsync(host):
    if not find_executable('rsync'):
        raise NotImplementedError('The `rsync` binary is not available on this system.')


def rsync(
    state, host, src, dest, flags,
    print_output=False, print_input=False,
    **command_kwargs
):
    status, _, stderr = run_shell_command(
        state, host,
        'rsync {0} {1} {2}'.format(' '.join(flags), src, dest),
        print_output=print_output,
        print_input=print_input,
        **command_kwargs
    )

    if not status:
        raise IOError('\n'.join(stderr))

    return True
