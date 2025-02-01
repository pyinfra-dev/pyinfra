from typing import Unpack, TYPE_CHECKING
from pyinfra.api.exceptions import InventoryError, ConnectError, PyinfraError
from pyinfra.api.util import memoize, get_file_io
from pyinfra.api.command import StringCommand, QuoteString
from pyinfra import logger
from pyinfra.connectors.ssh import SSHConnector
from pyinfra.connectors.base import BaseConnector
from pyinfra.connectors.util import extract_control_arguments
from pyinfra.progress import progress_spinner

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


@memoize
def show_warning():
    logger.warning("The @lxcssh connector is in alfa!")

class LxcSSHConnector(BaseConnector):
    """Connector for executing commands inside LXC (not lxd!) containers using SSH.
       Containers can be manageged by root (sudo needed) or other users.
       Inside the container execution is always as a root only.
    """

    has_copy = True
    has_get = True
    handles_execution = True

    @staticmethod
    def make_names_data(name):
        try:
            hostname, conatainer_name = name.split(":", 1)
        except (AttributeError, ValueError):  # failure to parse the name
            raise InventoryError("No ssh host or lxc base image provided!")

        if not conatainer_name:
            raise InventoryError("No container name provided!")

        show_warning()

        yield (
            "@lxcssh/{0}:{1}".format(hostname, conatainer_name),
            {"ssh_hostname": hostname, "lxc_container": conatainer_name},
            ["@lxcssh"],
        )

    def __init__(self, state: "State", host: "Host"):
        super().__init__(state, host)
        self.ssh = SSHConnector(state, host)

    def connect(self):
        """Connect to the LXC container via SSH."""
        self.ssh.connect()

        #TODO hack because of the sudo_password_path setting which calls back the run_shell_command for creation of ask_sudo_password file
        #     but wee need this file on the host, not inside the container, also who knows how the lxc-attach wrapping would work
        self.host.connector = self.ssh
        try:
            with progress_spinner({"lxc-info run"}):
                # Ensure the container is running
                command = StringCommand("lxc-info", "-n", self.host.data.lxc_container , "-s", "|", "grep", "RUNNING")
                status, output  = self.ssh.run_shell_command(command, _sudo=self.host.host_data["_sudo"], _sudo_password=self.host.host_data["_sudo_password"])
        except PyinfraError as e:
            raise ConnectError(e.args[0])
        finally:
            #TODO hack - see above
            self.host.connector = self

        if not status:
                raise ConnectError(f"LXC container {self.host.data.lxc_container} is not running")

        return True

    def run_shell_command(self,
        command,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ):
        """Run a command inside the LXC container.
           The command in container runs always as a root 
        """
        local_arguments = self._extract_local_args_sudo(arguments)
        container_name = self.host.data.get("lxc_container")
        lxc_cmd =  StringCommand("lxc-attach", "-n", container_name, " -- ", "sh", "-c", QuoteString(command))
        return self.ssh.run_shell_command(lxc_cmd, **local_arguments)


    def _get_container_pid(self, container_name,**arguments):
        """Retrieve the PID of the LXC container."""
        local_arguments = self._extract_local_args_sudo(arguments)
        #find the PID of the container
        cmd = StringCommand("lxc-info", "-n", container_name , "-p", "|", "awk", "'{{print $2}}'")
        status, output = self.ssh.run_shell_command(cmd, **local_arguments)
        if not status:
            raise ConnectError(f"Failed to get PID for LXC container {container_name}")
        return output.stdout.strip()


    def put_file(self, filename_or_io, remote_filename, 
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

        #1. put the file on host via non sudo user
        remote_temp_filename = remote_temp_filename or self.host.get_temp_filename(remote_filename)
        ssh_status = self.ssh.put_file(filename_or_io, remote_temp_filename)

        # 2. move inside the docker container through /proc/{PID}/root
        local_arguments = self._extract_local_args_sudo(kwargs)
        #TODO access rights might be different in the container?
        cmd = StringCommand("mv",  remote_temp_filename , f"/proc/{pid}/root{remote_filename}")
        status, output = self.ssh.run_shell_command(cmd, **local_arguments)
        return status

    def _extract_local_args_sudo(self, kwargs):
        local_arguments = extract_control_arguments(kwargs)
        local_arguments["_sudo"]=self.host.host_data["_sudo"]
        local_arguments["_sudo_password"]=self.host.host_data["_sudo_password"]
        return local_arguments


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
        pid = self._get_container_pid( container_name)
        local_arguments = self._extract_local_args_sudo(kwargs)
        return self.ssh.get_file(f"/proc/{pid}/root{remote_filename}", filename_or_io, remote_temp_filename, print_output, print_input, **local_arguments)


    def disconnect(self):
        #HACK - see above in def connect, this part is because systems deletes at the end the sudo_ask_password file
        self.host.connector = self.ssh

    def close(self, host):
        """Close the SSH connection."""
        self.ssh.close(host)
