"""
.. warning::
    This connector is in alpha and may change in future releases.

Some Windows facts and Windows operations work but this is to be considered
experimental. For now, only ``winrm_username`` and ``winrm_password`` is
being used. There are other methods for authentication, but they have not yet
been added/experimented with.

The ``@winrm`` connector can be used to communicate with Windows instances that have WinRM enabled.

Examples using ``@winrm``:

.. code:: python

    # Get the windows_home fact
    pyinfra @winrm/192.168.3.232 --winrm-username vagrant \\
        --winrm-password vagrant --winrm-port 5985 -vv --debug fact windows_home

    # Create a directory
    pyinfra @winrm/192.168.3.232 --winrm-username vagrant \\
        --winrm-password vagrant --winrm-port 5985 windows_files.windows_directory 'c:\temp'

    # Run a powershell command ('ps' is the default shell-executable for the winrm connector)
    pyinfra @winrm/192.168.3.232 --winrm-username vagrant \\
        --winrm-password vagrant --winrm-port 5985 exec -- write-host hello

    # Run a command using the command prompt:
    pyinfra @winrm/192.168.3.232 --winrm-username vagrant \\
        --winrm-password vagrant --winrm-port 5985 --shell-executable cmd exec -- date /T

    # Run a command using the winrm ntlm transport
    pyinfra @winrm/192.168.3.232 --winrm-username vagrant \\
        --winrm-password vagrant --winrm-port 5985 --winrm-transport ntlm exec -- hostname
"""

import base64
import ntpath

import click

from pyinfra import logger
from pyinfra.api.connectors import BaseConnectorMeta
from pyinfra.api.exceptions import ConnectError, PyinfraError
from pyinfra.api.util import get_file_io, memoize, sha1_hash

from .pyinfrawinrmsession import PyinfraWinrmSession
from .util import make_win_command


class Meta(BaseConnectorMeta):
    handles_execution = True
    keys_prefix = "winrm"

    class DataKeys:
        hostname = "WinRM hostname to connect to"
        port = "WinRM port to connect to"
        user = "WinRM username"
        password = "WinRM password"
        transport = "WinRM transport (default: ``plaintext``)"
        read_timeout_sec = "Read timeout in seconds (default: ``30``)"
        operation_timeout_sec = "Operation timeout in seconds (default: ``20``)"


DATA_KEYS = Meta.keys()


def _raise_connect_error(host, message, data):
    message = "{0} ({1})".format(message, data)
    raise ConnectError(message)


@memoize
def show_warning():
    logger.warning("The @winrm connector is alpha!")


def _make_winrm_kwargs(state, host):
    kwargs = {}

    for key, value in (
        ("username", host.data.get(DATA_KEYS.user)),
        ("password", host.data.get(DATA_KEYS.password)),
        ("winrm_port", int(host.data.get(DATA_KEYS.port, 0))),
        ("winrm_transport", host.data.get(DATA_KEYS.transport, "plaintext")),
        (
            "winrm_read_timeout_sec",
            host.data.get(DATA_KEYS.read_timeout_sec, 30),
        ),
        (
            "winrm_operation_timeout_sec",
            host.data.get(DATA_KEYS.operation_timeout_sec, 20),
        ),
    ):
        if value:
            kwargs[key] = value

    # FUTURE: add more auth
    # pywinrm supports: basic, certificate, ntlm, kerberos, plaintext, ssl, credssp
    # see https://github.com/diyan/pywinrm/blob/master/winrm/__init__.py#L12

    return kwargs


def make_names_data(hostname):

    show_warning()

    yield "@winrm/{0}".format(hostname), {"winrm_hostname": hostname}, []


def connect(state, host):
    """
    Connect to a single host. Returns the winrm Session if successful.
    """

    kwargs = _make_winrm_kwargs(state, host)
    logger.debug("Connecting to: %s (%s)", host.name, kwargs)

    # Hostname can be provided via winrm config (alias), data, or the hosts name
    hostname = kwargs.pop(
        "hostname",
        host.data.get(DATA_KEYS.hostname, host.name),
    )

    try:
        # Create new session
        host_and_port = "{}:{}".format(hostname, host.data.get(DATA_KEYS.port))
        logger.debug("host_and_port: %s", host_and_port)

        session = PyinfraWinrmSession(
            host_and_port,
            auth=(
                kwargs["username"],
                kwargs["password"],
            ),
            transport=kwargs["winrm_transport"],
            read_timeout_sec=kwargs["winrm_read_timeout_sec"],
            operation_timeout_sec=kwargs["winrm_operation_timeout_sec"],
        )

        return session

    # TODO: add exceptions here
    except Exception as e:
        auth_kwargs = {}

        for key, value in kwargs.items():
            if key in ("username", "password"):
                auth_kwargs[key] = value

        auth_args = ", ".join("{0}={1}".format(key, value) for key, value in auth_kwargs.items())
        logger.debug("%s", e)
        _raise_connect_error(host, "Authentication error", auth_args)


def run_shell_command(
    state,
    host,
    command,
    env=None,
    success_exit_codes=None,
    print_output=False,
    print_input=False,
    return_combined_output=False,
    shell_executable=None,
    **ignored_command_kwargs,
):
    """
    Execute a command on the specified host.

    Args:
        state (``pyinfra.api.State`` obj): state object for this command
        hostname (string): hostname of the target
        command (string): actual command to execute
        success_exit_codes (list): all values in the list that will return success
        print_output (boolean): print the output
        print_intput (boolean): print the input
        return_combined_output (boolean): combine the stdout and stderr lists
        shell_executable (string): shell to use - 'cmd'=cmd, 'ps'=powershell(default)
        env (dict): environment variables to set

    Returns:
        tuple: (exit_code, stdout, stderr)
        stdout and stderr are both lists of strings from each buffer.
    """

    command = make_win_command(command)

    logger.debug("Running command on %s: %s", host.name, command)

    if print_input:
        click.echo("{0}>>> {1}".format(host.print_prefix, command), err=True)

    # get rid of leading/trailing quote
    tmp_command = command.strip("'")

    if print_output:
        click.echo(
            "{0}>>> {1}".format(host.print_prefix, command),
            err=True,
        )

    if not shell_executable:
        shell_executable = "ps"
    logger.debug("shell_executable:%s", shell_executable)

    # we use our own subclassed session that allows for env setting from open_shell.
    if shell_executable in ["cmd"]:
        response = host.connection.run_cmd(tmp_command, env=env)
    else:
        response = host.connection.run_ps(tmp_command, env=env)

    return_code = response.status_code
    logger.debug("response:%s", response)

    std_out_str = response.std_out.decode("utf-8")
    std_err_str = response.std_err.decode("utf-8")

    # split on '\r\n' (windows newlines)
    std_out = std_out_str.split("\r\n")
    std_err = std_err_str.split("\r\n")

    logger.debug("std_out:%s", std_out)
    logger.debug("std_err:%s", std_err)

    if print_output:
        click.echo(
            "{0}>>> {1}".format(host.print_prefix, "\n".join(std_out)),
            err=True,
        )

    if success_exit_codes:
        status = return_code in success_exit_codes
    else:
        status = return_code == 0

    logger.debug("Command exit status: %s", status)

    if return_combined_output:
        std_out = [("stdout", line) for line in std_out]
        std_err = [("stderr", line) for line in std_err]
        return status, std_out + std_err

    return status, std_out, std_err


def get_file(
    state, host, remote_filename, filename_or_io, remote_temp_filename=None, **command_kwargs
):
    raise PyinfraError("Not implemented")


def _put_file(state, host, filename_or_io, remote_location, chunk_size=2048):
    # this should work fine on smallish files, but there will be perf issues
    # on larger files both due to the full read, the base64 encoding, and
    # the latency when sending chunks
    with get_file_io(filename_or_io) as file_io:
        data = file_io.read()
        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]
            ps = (
                '$data = [System.Convert]::FromBase64String("{0}"); '
                '{1} -Value $data -Encoding byte -Path "{2}"'
            ).format(
                base64.b64encode(chunk).decode("utf-8"),
                "Set-Content" if i == 0 else "Add-Content",
                remote_location,
            )
            status, _stdout, stderr = run_shell_command(state, host, ps)
            if status is False:
                logger.error("File upload error: {0}".format("\n".join(stderr)))
                return False

    return True


def put_file(
    state,
    host,
    filename_or_io,
    remote_filename,
    print_output=False,
    print_input=False,
    remote_temp_filename=None,  # ignored
    **command_kwargs,
):
    """
    Upload file by chunking and sending base64 encoded via winrm
    """

    # TODO: fix this? Workaround for circular import
    from pyinfra.facts.windows_files import TempDir

    # Always use temp file here in case of failure
    temp_file = ntpath.join(
        host.get_fact(TempDir),
        "pyinfra-{0}".format(sha1_hash(remote_filename)),
    )

    if not _put_file(state, host, filename_or_io, temp_file):
        return False

    # Execute run_shell_command w/sudo and/or su_user
    command = "Move-Item -Path {0} -Destination {1} -Force".format(temp_file, remote_filename)
    status, _, stderr = run_shell_command(
        state, host, command, print_output=print_output, print_input=print_input, **command_kwargs
    )

    if status is False:
        logger.error("File upload error: {0}".format("\n".join(stderr)))
        return False

    if print_output:
        click.echo(
            "{0}file uploaded: {1}".format(host.print_prefix, remote_filename),
            err=True,
        )

    return True
