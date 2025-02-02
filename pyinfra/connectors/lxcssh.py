from typing import TYPE_CHECKING

from typing_extensions import Unpack

from pyinfra import logger
from pyinfra.api.arguments import CONNECTOR_ARGUMENT_KEYS, pop_global_arguments
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.exceptions import ConnectError, InventoryError, PyinfraError
from pyinfra.api.util import memoize
from pyinfra.connectors.base import BaseConnector
from pyinfra.connectors.ssh import SSHConnector

if TYPE_CHECKING:
    from typing import Any

    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


@memoize
def show_warning():
    logger.warning("The @lxcssh connector is in alfa!")


class LxcSSHConnector(BaseConnector):
    """Connector for executing commands inside LXC (not lxd) containers using SSH to host.
    Containers can be managed by root (sudo needed) or other users.
    Inside the container execution is always as a root only.
    """

    __examples_doc__ = """
    An inventory file (``inventory.py``) for connection to lxc container via lxc (not lxd):

    .. code:: python

        hosts = [
            ("lxcssh/host_lxc:container_name"),
        ]

    pyinfra inventory.py deploy.py

    .. code:: python

        hosts = [
            ("lxcssh/host_lxc:container_name", {"more ssh params here, or sudo relateing params"}),
        ]

    Another possibility:
    * pyinfra @lxcssh/host_lxc.intranet:container_name exec hostname

    """

    has_copy = True
    has_get = True
    handles_execution = True

    @staticmethod
    def make_names_data(name):
        try:
            hostname, container_name = name.split(":", 1)
        except (AttributeError, ValueError):  # failure to parse the name
            raise InventoryError("No ssh host or lxc base image provided!")

        if not container_name:
            raise InventoryError("No container name provided!")

        show_warning()

        yield (
            "@lxcssh/{0}:{1}".format(hostname, container_name),
            {"ssh_hostname": hostname, "lxc_container": container_name},
            ["@lxcssh"],
        )

    def __init__(self, state: "State", host: "Host"):
        super().__init__(state, host)
        self.ssh = SSHConnector(state, host)

    def connect(self):
        """Connect to the LXC container via SSH."""
        self.ssh.connect()

        # TODO hack because of the sudo_password_path setting which calls back the run_shell_command
        #     for creation of ask_sudo_password file
        #     but wee need this file on the host, not inside the container
        self.host.connector = self.ssh

        # get us properly merged sudo params  (command line, host data etc..)
        # inspiration from def _handle_fact_kwargs in facts.py
        # TODO not sure if this is more correct
        # ctx_kwargs : dict[str, Any] = (self.host.current_op_global_arguments or {}).copy()
        ctx_kwargs: dict[str, Any] = {}
        global_kwargs, _ = pop_global_arguments(
            ctx_kwargs,
            state=self.state,
            host=self.host,
        )
        executor_kwargs: dict[str, Any] = {
            key: value for key, value in global_kwargs.items() if key in CONNECTOR_ARGUMENT_KEYS
        }

        try:
            status, _output = self.ssh.run_shell_command(
                StringCommand(
                    "lxc-info",
                    "-n",
                    self.host.data.lxc_container,
                    "-s",
                    "|",
                    "grep",
                    "RUNNING",
                ),
                False,
                False,
                **executor_kwargs,
            )
        except PyinfraError as e:
            raise ConnectError(e.args[0])
        finally:
            # TODO hack - see above
            self.host.connector = self

        if not status:
            raise ConnectError(f"LXC container {self.host.data.lxc_container} is not running")

        return True

    def run_shell_command(
        self,
        command,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ):
        """Run a command inside the LXC container.
        The command in container runs always as a root
        """
        container_name = self.host.data.get("lxc_container")
        lxc_cmd = StringCommand(
            "lxc-attach", "-n", container_name, " -- ", "sh", "-c", QuoteString(command)
        )
        return self.ssh.run_shell_command(lxc_cmd, **arguments)

    def _get_container_pid(self, container_name, **arguments):
        # find the PID of the container
        cmd = StringCommand("lxc-info", "-n", container_name, "-p", "|", "awk", "'{{print $2}}'")
        status, output = self.ssh.run_shell_command(cmd, **arguments)
        if not status:
            raise ConnectError(f"Failed to get PID for LXC container {container_name}")
        return output.stdout.strip()

    def put_file(
        self,
        filename_or_io,
        remote_filename,
        remote_temp_filename=None,
        print_output: bool = False,
        print_input: bool = False,
        **kwargs,  # ignored (sudo/etc)
    ):
        """Copy a file into the LXC container using /proc/[pid]/root."""
        container_name = self.host.data.get("lxc_container")
        if not container_name:
            raise ConnectError(f"No LXC container specified for {self.host}")

        pid = self._get_container_pid(container_name, **kwargs)

        # 1. put the file on host via non sudo user
        remote_temp_filename = remote_temp_filename or self.host.get_temp_filename(remote_filename)
        res_putfile = self.ssh.put_file(filename_or_io, remote_temp_filename)
        if not res_putfile:
            raise ConnectError(
                f"Uploading  {filename_or_io} to remote file {remote_temp_filename} failed."
            )

        # 2. move inside the docker container through /proc/{PID}/root

        # TODO access rights might be different in the container?
        cmd = StringCommand("mv", remote_temp_filename, f"/proc/{pid}/root{remote_filename}")
        status, output = self.ssh.run_shell_command(cmd, **kwargs)
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
        """Retrieve a file from the LXC container using /proc/[pid]/root."""
        container_name = self.host.data.get("lxc_container")
        pid = self._get_container_pid(container_name)
        return self.ssh.get_file(
            f"/proc/{pid}/root{remote_filename}",
            filename_or_io,
            remote_temp_filename,
            print_output,
            print_input,
            **kwargs,
        )

    def disconnect(self):
        # HACK - see above in def connect(self..), this part is because systems
        #        deletes the sudo_ask_password file at the end of the run
        self.host.connector = self.ssh
