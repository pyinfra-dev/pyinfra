import os
from tempfile import mkstemp
from typing import TYPE_CHECKING

import click
from typing_extensions import Unpack

from pyinfra import logger
from pyinfra.api import QuoteString, StringCommand
from pyinfra.api.exceptions import ConnectError, InventoryError, PyinfraError
from pyinfra.api.util import get_file_io, memoize
from pyinfra.progress import progress_spinner

from .base import BaseConnector
from .ssh import SSHConnector
from .util import extract_control_arguments, make_unix_command_for_host

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


@memoize
def show_warning():
    logger.warning("The @dockerssh connector is in beta!")


class DockerSSHConnector(BaseConnector):
    """
    **Note**: this connector is in beta!

    The ``@dockerssh`` connector allows you to run commands on Docker containers \
    on a remote machine.

    .. code:: shell

        # A Docker base image must be provided
        pyinfra @dockerssh/remotehost:alpine:3.8 ...

        # pyinfra can run on multiple Docker images in parallel
        pyinfra @dockerssh/remotehost:alpine:3.8,@dockerssh/remotehost:ubuntu:bionic ...
    """

    handles_execution = True

    ssh: SSHConnector

    def __init__(self, state: "State", host: "Host"):
        super().__init__(state, host)
        self.ssh = SSHConnector(state, host)

    @staticmethod
    def make_names_data(name):
        try:
            hostname, image = name.split(":", 1)
        except (AttributeError, ValueError):  # failure to parse the name
            raise InventoryError("No ssh host or docker base image provided!")

        if not image:
            raise InventoryError("No docker base image provided!")

        show_warning()

        yield (
            "@dockerssh/{0}:{1}".format(hostname, image),
            {"ssh_hostname": hostname, "docker_image": image},
            ["@dockerssh"],
        )

    def connect(self) -> None:
        self.ssh.connect()

        if "docker_container_id" in self.host.host_data:  # user can provide a docker_container_id
            return

        try:
            with progress_spinner({"docker run"}):
                # last line is the container ID
                status, output = self.ssh.run_shell_command(
                    StringCommand(
                        "docker",
                        "run",
                        "-d",
                        self.host.data.docker_image,
                        "tail",
                        "-f",
                        "/dev/null",
                    ),
                )
                if not status:
                    raise IOError(output.stderr)
                container_id = output.stdout_lines[-1]

        except PyinfraError as e:
            raise ConnectError(e.args[0])

        self.host.host_data["docker_container_id"] = container_id

    def disconnect(self) -> None:
        container_id = self.host.host_data["docker_container_id"][:12]

        with progress_spinner({"docker commit"}):
            _, output = self.ssh.run_shell_command(StringCommand("docker", "commit", container_id))

            # Last line is the image ID, get sha256:[XXXXXXXXXX]...
            image_id = output.stdout_lines[-1][7:19]

        with progress_spinner({"docker rm"}):
            self.ssh.run_shell_command(
                StringCommand("docker", "rm", "-f", container_id),
            )

        logger.info(
            "{0}docker build complete, image ID: {1}".format(
                self.host.print_prefix,
                click.style(image_id, bold=True),
            ),
        )

    def run_shell_command(
        self,
        command,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ):
        local_arguments = extract_control_arguments(arguments)

        container_id = self.host.host_data["docker_container_id"]

        command = make_unix_command_for_host(self.state, self.host, command, **arguments)
        command = QuoteString(command)

        docker_flags = "-it" if local_arguments.get("_get_pty") else "-i"
        docker_command = StringCommand(
            "docker",
            "exec",
            docker_flags,
            container_id,
            "sh",
            "-c",
            command,
        )

        return self.ssh.run_shell_command(
            docker_command,
            print_output=print_output,
            print_input=print_input,
            **local_arguments,
        )

    def put_file(
        self,
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
        remote_temp_filename = remote_temp_filename or self.host.get_temp_filename(
            local_temp_filename
        )

        # Load our file or IO object and write it to the temporary file
        with get_file_io(filename_or_io) as file_io:
            with open(local_temp_filename, "wb") as temp_f:
                data = file_io.read()

                if isinstance(data, str):
                    data = data.encode()

                temp_f.write(data)

        # upload file to remote server
        ssh_status = self.ssh.put_file(local_temp_filename, remote_temp_filename)
        if not ssh_status:
            raise IOError("Failed to copy file over ssh")

        try:
            docker_id = self.host.host_data["docker_container_id"]
            docker_command = StringCommand(
                "docker",
                "cp",
                remote_temp_filename,
                f"{docker_id}:{remote_filename}",
            )

            status, output = self.ssh.run_shell_command(
                docker_command,
                print_output=print_output,
                print_input=print_input,
            )
        finally:
            os.close(fd)
            os.remove(local_temp_filename)
            self.remote_remove(
                local_temp_filename,
                print_output=print_output,
                print_input=print_input,
            )

        if not status:
            raise IOError(output.stderr)

        if print_output:
            click.echo(
                "{0}file uploaded to container: {1}".format(
                    self.host.print_prefix,
                    remote_filename,
                ),
                err=True,
            )

        return status

    def get_file(
        self,
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

        remote_temp_filename = remote_temp_filename or self.host.get_temp_filename(remote_filename)

        try:
            docker_id = self.host.host_data["docker_container_id"]
            docker_command = StringCommand(
                "docker",
                "cp",
                f"{docker_id}:{remote_filename}",
                remote_temp_filename,
            )

            status, output = self.ssh.run_shell_command(
                docker_command,
                print_output=print_output,
                print_input=print_input,
            )

            ssh_status = self.ssh.get_file(remote_temp_filename, filename_or_io)
        finally:
            self.remote_remove(
                remote_temp_filename,
                print_output=print_output,
                print_input=print_input,
            )

        if not ssh_status:
            raise IOError("failed to copy file over ssh")

        if not status:
            raise IOError(output.stderr)

        if print_output:
            click.echo(
                "{0}file downloaded from container: {1}".format(
                    self.host.print_prefix,
                    remote_filename,
                ),
                err=True,
            )

        return status

    def remote_remove(self, filename, print_output: bool = False, print_input: bool = False):
        """
        Deletes a file on a remote machine over ssh.
        """
        remove_status, output = self.ssh.run_shell_command(
            StringCommand("rm", "-f", filename),
            print_output=print_output,
            print_input=print_input,
        )

        if not remove_status:
            raise IOError(output.stderr)
