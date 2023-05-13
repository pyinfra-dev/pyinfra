"""
Connect to hosts over SSH. This is the default connector and all targets default
to this meaning you do not need to specify it - ie the following two commands
are identical:

.. code:: shell

    pyinfra my-host.net ...
    pyinfra @ssh/my-host.net ...
"""
import shlex
from distutils.spawn import find_executable
from getpass import getpass
from os import path
from socket import error as socket_error, gaierror
from typing import TYPE_CHECKING, Type, Union

import click
from paramiko import (
    AuthenticationException,
    BadHostKeyException,
    DSSKey,
    ECDSAKey,
    Ed25519Key,
    PasswordRequiredException,
    RSAKey,
    SFTPClient,
    SSHException,
)

import pyinfra
from pyinfra import logger
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.connectors import BaseConnectorMeta
from pyinfra.api.exceptions import ConnectError, PyinfraError
from pyinfra.api.util import get_file_io, memoize

from .sshuserclient import SSHClient
from .util import (
    execute_command_with_sudo_retry,
    make_unix_command_for_host,
    read_buffers_into_queue,
    run_local_process,
    split_combined_output,
    write_stdin,
)

if TYPE_CHECKING:
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


class Meta(BaseConnectorMeta):
    handles_execution = True
    keys_prefix = "ssh"

    class DataKeys:
        hostname = "SSH hostname"
        port = "SSH port"

        user = "User to SSH as"
        password = "Password to use for authentication"
        key = "Key file to use for authentication"
        key_password = "Key file password"

        allow_agent = "Allow using SSH agent"
        look_for_keys = "Allow looking up users keys"

        forward_agent = "Enable SSH forward agent"
        config_file = "Custom SSH config file"
        known_hosts_file = "Custom SSH known hosts file"
        strict_host_key_checking = "Override strict host keys check setting"

        paramiko_connect_kwargs = (
            "Override keyword arguments passed into paramiko's `SSHClient.connect`"
        )


DATA_KEYS = Meta.keys()


def make_names_data(hostname):
    yield "@ssh/{0}".format(hostname), {DATA_KEYS.hostname: hostname}, []


def _raise_connect_error(host: "Host", message, data):
    message = "{0} ({1})".format(message, data)
    raise ConnectError(message)


def _load_private_key_file(filename: str, key_filename: str, key_password: str):
    exception: Union[PyinfraError, SSHException] = PyinfraError("Invalid key: {0}".format(filename))

    key_cls: Union[Type[RSAKey], Type[DSSKey], Type[ECDSAKey], Type[Ed25519Key]]

    for key_cls in (RSAKey, DSSKey, ECDSAKey, Ed25519Key):
        try:
            return key_cls.from_private_key_file(
                filename=filename,
            )

        except PasswordRequiredException:
            if not key_password:
                # If password is not provided, but we're in CLI mode, ask for it. I'm not a
                # huge fan of having CLI specific code in here, but it doesn't really fit
                # anywhere else without duplicating lots of key related code into cli.py.
                if pyinfra.is_cli:
                    key_password = getpass(
                        "Enter password for private key: {0}: ".format(
                            key_filename,
                        ),
                    )

                # API mode and no password? We can't continue!
                else:
                    raise PyinfraError(
                        "Private key file ({0}) is encrypted, set ssh_key_password to "
                        "use this key".format(key_filename),
                    )

            try:
                return key_cls.from_private_key_file(
                    filename=filename,
                    password=key_password,
                )
            except SSHException as e:  # key does not match key_cls type
                exception = e
        except SSHException as e:  # key does not match key_cls type
            exception = e
    raise exception


def _get_private_key(state: "State", key_filename: str, key_password: str):
    if key_filename in state.private_keys:
        return state.private_keys[key_filename]

    ssh_key_filenames = [
        # Global from executed directory
        path.expanduser(key_filename),
    ]

    if state.cwd:
        # Relative to the CWD
        path.join(state.cwd, key_filename)

    key = None
    key_file_exists = False

    for filename in ssh_key_filenames:
        if not path.isfile(filename):
            continue

        key_file_exists = True

        try:
            key = _load_private_key_file(filename, key_filename, key_password)
            break
        except SSHException:
            pass

    # No break, so no key found
    if not key:
        if not key_file_exists:
            raise PyinfraError("No such private key file: {0}".format(key_filename))
        raise PyinfraError("Invalid private key file: {0}".format(key_filename))

    # Load any certificate, names from OpenSSH:
    # https://github.com/openssh/openssh-portable/blob/049297de975b92adcc2db77e3fb7046c0e3c695d/ssh-keygen.c#L2453  # noqa: E501
    for certificate_filename in (
        "{0}-cert.pub".format(key_filename),
        "{0}.pub".format(key_filename),
    ):
        if path.isfile(certificate_filename):
            key.load_certificate(certificate_filename)

    state.private_keys[key_filename] = key
    return key


def _make_paramiko_kwargs(state: "State", host: "Host"):
    kwargs = {
        "allow_agent": False,
        "look_for_keys": False,
        "hostname": host.data.get(DATA_KEYS.hostname, host.name),
        # Overrides of SSH config via pyinfra host data
        "_pyinfra_ssh_forward_agent": host.data.get(DATA_KEYS.forward_agent),
        "_pyinfra_ssh_config_file": host.data.get(DATA_KEYS.config_file),
        "_pyinfra_ssh_known_hosts_file": host.data.get(DATA_KEYS.known_hosts_file),
        "_pyinfra_ssh_strict_host_key_checking": host.data.get(DATA_KEYS.strict_host_key_checking),
        "_pyinfra_ssh_paramiko_connect_kwargs": host.data.get(DATA_KEYS.paramiko_connect_kwargs),
    }

    for key, value in (
        ("username", host.data.get(DATA_KEYS.user)),
        ("port", int(host.data.get(DATA_KEYS.port, 0))),
        ("timeout", state.config.CONNECT_TIMEOUT),
    ):
        if value:
            kwargs[key] = value

    # Password auth (boo!)
    ssh_password = host.data.get(DATA_KEYS.password)
    if ssh_password:
        kwargs["password"] = ssh_password

    # Key auth!
    ssh_key = host.data.get(DATA_KEYS.key)
    if ssh_key:
        kwargs["pkey"] = _get_private_key(
            state,
            key_filename=ssh_key,
            key_password=host.data.get(DATA_KEYS.key_password),
        )

    # No key or password, so let's have paramiko look for SSH agents and user keys
    # unless disabled by the user.
    else:
        kwargs["allow_agent"] = host.data.get(DATA_KEYS.allow_agent, True)
        kwargs["look_for_keys"] = host.data.get(DATA_KEYS.look_for_keys, True)

    return kwargs


def connect(state: "State", host: "Host"):
    """
    Connect to a single host. Returns the SSH client if successful. Stateless by
    design so can be run in parallel.
    """

    kwargs = _make_paramiko_kwargs(state, host)
    logger.debug("Connecting to: %s (%r)", host.name, kwargs)

    hostname = kwargs.pop("hostname")

    try:
        # Create new client & connect to the host
        client = SSHClient()
        client.connect(hostname, **kwargs)
        return client

    except AuthenticationException as e:
        auth_kwargs = {}

        for key, value in kwargs.items():
            if key in ("username", "password"):
                auth_kwargs[key] = value
                continue

            if key == "pkey" and value:
                auth_kwargs["key"] = host.data.get(DATA_KEYS.key)

        auth_args = ", ".join("{0}={1}".format(key, value) for key, value in auth_kwargs.items())

        _raise_connect_error(host, "Authentication error ({0})".format(auth_args), e)

    except BadHostKeyException as e:
        remove_entry = e.hostname
        port = client._ssh_config.get("port", 22)
        if port != 22:
            remove_entry = f"[{e.hostname}]:{port}"

        logger.warning("WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!")
        logger.warning(
            ("Someone could be eavesdropping on you right now " "(man-in-the-middle attack)!"),
        )
        logger.warning("If this is expected, you can remove the bad key using:")
        logger.warning(f"    ssh-keygen -R {remove_entry}")

        _raise_connect_error(
            host,
            "SSH host key error",
            f"Host key for {e.hostname} does not match.",
        )

    except SSHException as e:
        _raise_connect_error(host, "SSH error", e)

    except gaierror:
        _raise_connect_error(host, "Could not resolve hostname", hostname)

    except socket_error as e:
        _raise_connect_error(host, "Could not connect", e)

    except EOFError as e:
        _raise_connect_error(host, "EOF error", e)


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
    return_combined_output: bool = False,
    **command_kwargs,
):
    """
    Execute a command on the specified host.

    Args:
        state (``pyinfra.api.State`` obj): state object for this command
        hostname (string): hostname of the target
        command (string): actual command to execute
        sudo (boolean): whether to wrap the command with sudo
        sudo_user (string): user to sudo to
        get_pty (boolean): whether to get a PTY before executing the command
        env (dict): environment variables to set
        timeout (int): timeout for this command to complete before erroring

    Returns:
        tuple: (exit_code, stdout, stderr)
        stdout and stderr are both lists of strings from each buffer.
    """

    def execute_command():
        unix_command = make_unix_command_for_host(state, host, command, **command_kwargs)
        actual_command = unix_command.get_raw_value()

        logger.debug(
            "Running command on %s: (pty=%s) %s",
            host.name,
            get_pty,
            unix_command,
        )

        if print_input:
            click.echo("{0}>>> {1}".format(host.print_prefix, unix_command), err=True)

        # Run it! Get stdout, stderr & the underlying channel
        stdin_buffer, stdout_buffer, stderr_buffer = host.connection.exec_command(
            actual_command,
            get_pty=get_pty,
        )

        if stdin:
            write_stdin(stdin, stdin_buffer)

        combined_output = read_buffers_into_queue(
            stdout_buffer,
            stderr_buffer,
            timeout=timeout,
            print_output=print_output,
            print_prefix=host.print_prefix,
        )

        logger.debug("Waiting for exit status...")
        exit_status = stdout_buffer.channel.recv_exit_status()
        logger.debug("Command exit status: %i", exit_status)

        return exit_status, combined_output

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


@memoize
def _get_sftp_connection(host: "Host"):
    assert host.connection is not None
    transport = host.connection.get_transport()

    try:
        return SFTPClient.from_transport(transport)
    except SSHException as e:
        raise ConnectError(
            (
                "Unable to establish SFTP connection. Check that the SFTP subsystem "
                "for the SSH service at {0} is enabled."
            ).format(host),
        ) from e


def _get_file(host: "Host", remote_filename: str, filename_or_io):
    with get_file_io(filename_or_io, "wb") as file_io:
        sftp = _get_sftp_connection(host)
        sftp.getfo(remote_filename, file_io)


def get_file(
    state: "State",
    host: "Host",
    remote_filename: str,
    filename_or_io,
    remote_temp_filename=None,
    sudo: bool = False,
    sudo_user=None,
    su_user=None,
    print_output: bool = False,
    print_input: bool = False,
    **command_kwargs,
):
    """
    Download a file from the remote host using SFTP. Supports download files
    with sudo by copying to a temporary directory with read permissions,
    downloading and then removing the copy.
    """

    if sudo or su_user:
        # Get temp file location
        temp_file = remote_temp_filename or state.get_temp_filename(remote_filename)

        # Copy the file to the tempfile location and add read permissions
        command = "cp {0} {1} && chmod +r {0}".format(remote_filename, temp_file)

        copy_status, _, stderr = run_shell_command(
            state,
            host,
            command,
            sudo=sudo,
            sudo_user=sudo_user,
            su_user=su_user,
            print_output=print_output,
            print_input=print_input,
            **command_kwargs,
        )

        if copy_status is False:
            logger.error("File download copy temp error: {0}".format("\n".join(stderr)))
            return False

        try:
            _get_file(host, temp_file, filename_or_io)

        # Ensure that, even if we encounter an error, we (attempt to) remove the
        # temporary copy of the file.
        finally:
            remove_status, _, stderr = run_shell_command(
                state,
                host,
                "rm -f {0}".format(temp_file),
                sudo=sudo,
                sudo_user=sudo_user,
                su_user=su_user,
                print_output=print_output,
                print_input=print_input,
                **command_kwargs,
            )

        if remove_status is False:
            logger.error("File download remove temp error: {0}".format("\n".join(stderr)))
            return False

    else:
        _get_file(host, remote_filename, filename_or_io)

    if print_output:
        click.echo(
            "{0}file downloaded: {1}".format(host.print_prefix, remote_filename),
            err=True,
        )

    return True


def _put_file(host: "Host", filename_or_io, remote_location):
    logger.debug("Attempting upload of %s to %s", filename_or_io, remote_location)

    attempts = 0
    last_e = None

    while attempts < 3:
        try:
            with get_file_io(filename_or_io) as file_io:
                sftp = _get_sftp_connection(host)
                sftp.putfo(file_io, remote_location)
            return
        except OSError as e:
            logger.warning(f"Failed to upload file, retrying: {e}")
            attempts += 1
            last_e = e

    if last_e is not None:
        raise last_e


def put_file(
    state: "State",
    host: "Host",
    filename_or_io,
    remote_filename,
    remote_temp_filename=None,
    sudo: bool = False,
    sudo_user=None,
    doas: bool = False,
    doas_user=None,
    su_user=None,
    print_output: bool = False,
    print_input: bool = False,
    **command_kwargs,
):
    """
    Upload file-ios to the specified host using SFTP. Supports uploading files
    with sudo by uploading to a temporary directory then moving & chowning.
    """

    # sudo/su are a little more complicated, as you can only sftp with the SSH
    # user connected, so upload to tmp and copy/chown w/sudo and/or su_user
    if sudo or doas or su_user:
        # Get temp file location
        temp_file = remote_temp_filename or state.get_temp_filename(remote_filename)
        _put_file(host, filename_or_io, temp_file)

        # Make sure our sudo/su user can access the file
        if su_user:
            command = StringCommand("setfacl", "-m", "u:{0}:r".format(su_user), temp_file)
        elif sudo_user:
            command = StringCommand("setfacl", "-m", "u:{0}:r".format(sudo_user), temp_file)
        elif doas_user:
            command = StringCommand("setfacl", "-m", "u:{0}:r".format(doas_user), temp_file)

        if su_user or sudo_user or doas_user:
            status, _, stderr = run_shell_command(
                state,
                host,
                command,
                sudo=False,
                print_output=print_output,
                print_input=print_input,
                **command_kwargs,
            )

            if status is False:
                logger.error("Error on handover to sudo/su user: {0}".format("\n".join(stderr)))
                return False

        # Execute run_shell_command w/sudo and/or su_user
        command = StringCommand("cp", temp_file, QuoteString(remote_filename))

        status, _, stderr = run_shell_command(
            state,
            host,
            command,
            sudo=sudo,
            sudo_user=sudo_user,
            doas=doas,
            doas_user=doas_user,
            su_user=su_user,
            print_output=print_output,
            print_input=print_input,
            **command_kwargs,
        )

        if status is False:
            logger.error("File upload error: {0}".format("\n".join(stderr)))
            return False

        # Delete the temporary file now that we've successfully copied it
        command = StringCommand("rm", "-f", temp_file)

        status, _, stderr = run_shell_command(
            state,
            host,
            command,
            sudo=False,
            doas=False,
            print_output=print_output,
            print_input=print_input,
            **command_kwargs,
        )

        if status is False:
            logger.error("Unable to remove temporary file: {0}".format("\n".join(stderr)))
            return False

    # No sudo and no su_user, so just upload it!
    else:
        _put_file(host, filename_or_io, remote_filename)

    if print_output:
        click.echo(
            "{0}file uploaded: {1}".format(host.print_prefix, remote_filename),
            err=True,
        )

    return True


def check_can_rsync(host: "Host"):
    if host.data.get(DATA_KEYS.key_password):
        raise NotImplementedError("Rsync does not currently work with SSH keys needing passwords.")

    if host.data.get(DATA_KEYS.password):
        raise NotImplementedError("Rsync does not currently work with SSH passwords.")

    if not find_executable("rsync"):
        raise NotImplementedError("The `rsync` binary is not available on this system.")


def rsync(
    state: "State",
    host: "Host",
    src: str,
    dest: str,
    flags,
    print_output: bool = False,
    print_input: bool = False,
    sudo: bool = False,
    sudo_user=None,
    **ignored_kwargs,
):
    hostname = host.data.get(DATA_KEYS.hostname, host.name)
    user = host.data.get(DATA_KEYS.user, "")
    if user:
        user = "{0}@".format(user)

    ssh_flags = []
    # To avoid asking for interactive input, specify BatchMode=yes
    ssh_flags.append("-o BatchMode=yes")

    known_hosts_file = host.data.get(DATA_KEYS.known_hosts_file, "")
    if known_hosts_file:
        ssh_flags.append(
            '-o \\"UserKnownHostsFile={0}\\"'.format(shlex.quote(known_hosts_file))
        )  # never trust users

    strict_host_key_checking = host.data.get(DATA_KEYS.strict_host_key_checking, "")
    if strict_host_key_checking:
        ssh_flags.append(
            '-o \\"StrictHostKeyChecking={0}\\"'.format(shlex.quote(strict_host_key_checking))
        )

    ssh_config_file = host.data.get(DATA_KEYS.config_file, "")
    if ssh_config_file:
        ssh_flags.append("-F {0}".format(shlex.quote(ssh_config_file)))

    port = host.data.get(DATA_KEYS.port)
    if port:
        ssh_flags.append("-p {0}".format(port))

    ssh_key = host.data.get(DATA_KEYS.key)
    if ssh_key:
        ssh_flags.append("-i {0}".format(ssh_key))

    remote_rsync_command = "rsync"
    if sudo:
        remote_rsync_command = "sudo rsync"
        if sudo_user:
            remote_rsync_command = "sudo -u {0} rsync".format(sudo_user)

    rsync_command = (
        "rsync {rsync_flags} "
        '--rsh "ssh {ssh_flags}" '
        "--rsync-path '{remote_rsync_command}' "
        "{src} {user}{hostname}:{dest}"
    ).format(
        rsync_flags=" ".join(flags),
        ssh_flags=" ".join(ssh_flags),
        remote_rsync_command=remote_rsync_command,
        user=user,
        hostname=hostname,
        src=src,
        dest=dest,
    )

    if print_input:
        click.echo("{0}>>> {1}".format(host.print_prefix, rsync_command), err=True)

    return_code, combined_output = run_local_process(
        rsync_command,
        print_output=print_output,
        print_prefix=host.print_prefix,
    )

    status = return_code == 0

    if not status:
        _, stderr = split_combined_output(combined_output)
        raise IOError("\n".join(stderr))

    return True
