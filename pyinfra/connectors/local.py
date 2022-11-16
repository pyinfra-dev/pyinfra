"""
The ``@local`` connector executes changes on the local machine using subprocesses.
"""

import os
from distutils.spawn import find_executable
from tempfile import mkstemp
from typing import TYPE_CHECKING

import click

from pyinfra import logger
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.connectors import BaseConnectorMeta
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import get_file_io

from .util import (
    execute_command_with_sudo_retry,
    make_unix_command_for_host,
    run_local_process,
    split_combined_output,
)

if TYPE_CHECKING:
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


class Meta(BaseConnectorMeta):
    handles_execution = True


def make_names_data(_=None):
    if _ is not None:
        raise InventoryError("Cannot have more than one @local")

    yield "@local", {}, ["@local"]


def connect(state: "State", host: "Host"):
    return True


def run_shell_command(
    state: "State",
    host: "Host",
    command,
    get_pty: bool = False,  # ignored
    timeout=None,
    stdin=None,
    success_exit_codes=None,
    print_output: bool = False,
    print_input: bool = False,
    return_combined_output: bool = False,
    **command_kwargs,
):
    """
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
    """

    def execute_command():
        unix_command = make_unix_command_for_host(state, host, command, **command_kwargs)
        actual_command = unix_command.get_raw_value()

        logger.debug("--> Running command on localhost: %s", unix_command)

        if print_input:
            click.echo("{0}>>> {1}".format(host.print_prefix, unix_command), err=True)

        return run_local_process(
            actual_command,
            stdin=stdin,
            timeout=timeout,
            print_output=print_output,
            print_prefix=host.print_prefix,
        )

    return_code, combined_output = execute_command_with_sudo_retry(
        host,
        command_kwargs,
        execute_command,
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
    state: "State",
    host: "Host",
    filename_or_io,
    remote_filename,
    remote_temp_filename=None,  # ignored
    print_output: bool = False,
    print_input: bool = False,
    **command_kwargs,
):
    """
    Upload a local file or IO object by copying it to a temporary directory
    and then writing it to the upload location.
    """

    _, temp_filename = mkstemp()

    try:
        # Load our file or IO object and write it to the temporary file
        with get_file_io(filename_or_io) as file_io:
            with open(temp_filename, "wb") as temp_f:
                data = file_io.read()

                if isinstance(data, str):
                    data = data.encode()

                temp_f.write(data)

        # Copy the file using `cp` such that we support sudo/su
        status, _, stderr = run_shell_command(
            state,
            host,
            StringCommand("cp", temp_filename, QuoteString(remote_filename)),
            print_output=print_output,
            print_input=print_input,
            **command_kwargs,
        )

        if not status:
            raise IOError("\n".join(stderr))
    finally:
        os.remove(temp_filename)

    if print_output:
        click.echo(
            "{0}file copied: {1}".format(host.print_prefix, remote_filename),
            err=True,
        )

    return status


def get_file(
    state: "State",
    host: "Host",
    remote_filename,
    filename_or_io,
    remote_temp_filename=None,  # ignored
    print_output: bool = False,
    print_input: bool = False,
    **command_kwargs,
):
    """
    Download a local file by copying it to a temporary location and then writing
    it to our filename or IO object.
    """

    _, temp_filename = mkstemp()

    try:
        # Copy the file using `cp` such that we support sudo/su
        status, _, stderr = run_shell_command(
            state,
            host,
            "cp {0} {1}".format(remote_filename, temp_filename),
            print_output=print_output,
            print_input=print_input,
            **command_kwargs,
        )

        if not status:
            raise IOError("\n".join(stderr))

        # Load our file or IO object and write it to the temporary file
        with open(temp_filename, encoding="utf-8") as temp_f:
            with get_file_io(filename_or_io, "wb") as file_io:
                data_bytes: bytes

                data = temp_f.read()
                if isinstance(data, str):
                    data_bytes = data.encode()
                else:
                    data_bytes = data

                file_io.write(data_bytes)
    finally:
        os.remove(temp_filename)

    if print_output:
        click.echo(
            "{0}file copied: {1}".format(host.print_prefix, remote_filename),
            err=True,
        )

    return True


def check_can_rsync(host):
    if not find_executable("rsync"):
        raise NotImplementedError("The `rsync` binary is not available on this system.")


def rsync(
    state: "State",
    host: "Host",
    src,
    dest,
    flags,
    print_output: bool = False,
    print_input: bool = False,
    **command_kwargs,
):
    status, _, stderr = run_shell_command(
        state,
        host,
        "rsync {0} {1} {2}".format(" ".join(flags), src, dest),
        print_output=print_output,
        print_input=print_input,
        **command_kwargs,
    )

    if not status:
        raise IOError("\n".join(stderr))

    return True
