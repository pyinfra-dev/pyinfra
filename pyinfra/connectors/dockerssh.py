"""
**Note**: this connector is in beta!

The ``@dockerssh`` connector allows you to run commands on Docker containers on a remote machine.

.. code:: shell

    # A Docker base image must be provided
    pyinfra @dockerssh/remotehost:alpine:3.8 ...

    # pyinfra can run on multiple Docker images in parallel
    pyinfra @dockerssh/remotehost:alpine:3.8,@dockerssh/remotehost:ubuntu:bionic ...
"""

import os
from tempfile import mkstemp
from typing import TYPE_CHECKING

import click

from pyinfra import logger
from pyinfra.api import QuoteString, StringCommand
from pyinfra.api.connectors import BaseConnectorMeta
from pyinfra.api.exceptions import ConnectError, InventoryError, PyinfraError
from pyinfra.api.util import get_file_io, memoize
from pyinfra.progress import progress_spinner

from . import ssh
from .util import make_unix_command_for_host

if TYPE_CHECKING:
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


class Meta(BaseConnectorMeta):
    handles_execution = True


def remote_remove(
    state: "State", host: "Host", filename, print_output: bool = False, print_input: bool = False
):
    """
    Deletes a file on a remote machine over ssh.
    """
    remove_status, _, remove_stderr = ssh.run_shell_command(
        state,
        host,
        "rm -f {0}".format(filename),
        print_output=print_output,
        print_input=print_input,
    )

    if not remove_status:
        raise IOError("\n".join(remove_stderr))


@memoize
def show_warning():
    logger.warning("The @dockerssh connector is in beta!")


def make_names_data(host_image_str):
    try:
        hostname, image = host_image_str.split(":", 1)
    except (AttributeError, ValueError):  # failure to parse the host_image_str
        raise InventoryError("No ssh host or docker base image provided!")

    if not image:
        raise InventoryError("No docker base image provided!")

    show_warning()

    yield (
        "@dockerssh/{0}:{1}".format(hostname, image),
        {"ssh_hostname": hostname, "docker_image": image},
        ["@dockerssh"],
    )


def connect(state: "State", host: "Host"):
    if not host.connection:
        host.connection = ssh.connect(state, host)

    if "docker_container_id" in host.host_data:  # user can provide a docker_container_id
        return host.connection

    try:
        with progress_spinner({"docker run"}):
            # last line is the container ID
            status, stdout, stderr = ssh.run_shell_command(
                state,
                host,
                "docker run -d {0} tail -f /dev/null".format(host.data.docker_image),
            )
            if not status:
                raise IOError("\n".join(stderr))
            container_id = stdout[-1]

    except PyinfraError as e:
        host.connection = None  # fail connection
        raise ConnectError(e.args[0])

    host.host_data["docker_container_id"] = container_id
    return host.connection


def disconnect(state: "State", host: "Host"):
    container_id = host.host_data["docker_container_id"][:12]

    with progress_spinner({"docker commit"}):
        image_id = ssh.run_shell_command(state, host, "docker commit {0}".format(container_id))[1][
            -1
        ][
            7:19
        ]  # last line is the image ID, get sha256:[XXXXXXXXXX]...

    with progress_spinner({"docker rm"}):
        ssh.run_shell_command(
            state,
            host,
            "docker rm -f {0}".format(container_id),
        )

    logger.info(
        "{0}docker build complete, image ID: {1}".format(
            host.print_prefix,
            click.style(image_id, bold=True),
        ),
    )


def run_shell_command(
    state: "State",
    host: "Host",
    command,
    get_pty: bool = False,
    timeout=None,
    stdin=None,
    success_exit_codes=None,
    print_output: bool = False,
    print_input: bool = False,
    return_combined_output=False,
    **command_kwargs,
):
    container_id = host.host_data["docker_container_id"]

    # Don't sudo/su in Docker - is this the right thing to do? Makes deploys that
    # target SSH systems work w/Docker out of the box (ie most docker commands
    # are run as root).
    for key in ("sudo", "su_user"):
        command_kwargs.pop(key, None)

    command = make_unix_command_for_host(state, host, command, **command_kwargs)
    command = QuoteString(command)

    docker_flags = "-it" if get_pty else "-i"
    docker_command = StringCommand(
        "docker",
        "exec",
        docker_flags,
        container_id,
        "sh",
        "-c",
        command,
    )

    return ssh.run_shell_command(
        state,
        host,
        docker_command,
        timeout=timeout,
        stdin=stdin,
        success_exit_codes=success_exit_codes,
        print_output=print_output,
        print_input=print_input,
        return_combined_output=return_combined_output,
    )


def put_file(
    state: "State",
    host: "Host",
    filename_or_io,
    remote_filename,
    remote_temp_filename=None,
    print_output: bool = False,
    print_input: bool = False,
    **kwargs,  # ignored (sudo/etc)
):
    """
    Upload a file/IO object to the target Docker container by copying it to a
    temporary location and then uploading it into the container using ``docker cp``.
    """

    fd, local_temp_filename = mkstemp()
    remote_temp_filename = remote_temp_filename or state.get_temp_filename(local_temp_filename)

    # Load our file or IO object and write it to the temporary file
    with get_file_io(filename_or_io) as file_io:
        with open(local_temp_filename, "wb") as temp_f:
            data = file_io.read()

            if isinstance(data, str):
                data = data.encode()

            temp_f.write(data)

    # upload file to remote server
    ssh_status = ssh.put_file(state, host, local_temp_filename, remote_temp_filename)
    if not ssh_status:
        raise IOError("Failed to copy file over ssh")

    try:
        docker_id = host.host_data["docker_container_id"]
        docker_command = "docker cp {0} {1}:{2}".format(
            remote_temp_filename,
            docker_id,
            remote_filename,
        )

        status, _, stderr = ssh.run_shell_command(
            state,
            host,
            docker_command,
            print_output=print_output,
            print_input=print_input,
        )
    finally:
        os.close(fd)
        os.remove(local_temp_filename)
        remote_remove(
            state,
            host,
            local_temp_filename,
            print_output=print_output,
            print_input=print_input,
        )

    if not status:
        raise IOError("\n".join(stderr))

    if print_output:
        click.echo(
            "{0}file uploaded to container: {1}".format(
                host.print_prefix,
                remote_filename,
            ),
            err=True,
        )

    return status


def get_file(
    state: "State",
    host: "Host",
    remote_filename,
    filename_or_io,
    remote_temp_filename=None,
    print_output: bool = False,
    print_input: bool = False,
    **kwargs,  # ignored (sudo/etc)
):
    """
    Download a file from the target Docker container by copying it to a temporary
    location and then reading that into our final file/IO object.
    """

    remote_temp_filename = remote_temp_filename or state.get_temp_filename(remote_filename)

    try:
        docker_id = host.host_data["docker_container_id"]
        docker_command = "docker cp {0}:{1} {2}".format(
            docker_id,
            remote_filename,
            remote_temp_filename,
        )

        status, _, stderr = ssh.run_shell_command(
            state,
            host,
            docker_command,
            print_output=print_output,
            print_input=print_input,
        )

        ssh_status = ssh.get_file(state, host, remote_temp_filename, filename_or_io)
    finally:
        remote_remove(
            state,
            host,
            remote_temp_filename,
            print_output=print_output,
            print_input=print_input,
        )

    if not ssh_status:
        raise IOError("failed to copy file over ssh")

    if not status:
        raise IOError("\n".join(stderr))

    if print_output:
        click.echo(
            "{0}file downloaded from container: {1}".format(
                host.print_prefix,
                remote_filename,
            ),
            err=True,
        )

    return status
