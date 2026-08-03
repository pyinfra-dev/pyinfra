"""
Execute commands and up/download files *from* the remote host.

Eg: ``pyinfra -> inventory-host.net <-> another-host.net``
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import OperationError, QuoteString, StringCommand, operation
from pyinfra.facts.files import File, FindInFile
from pyinfra.facts.server import Home

from . import files


@operation()
def keyscan(hostname: str, force=False, port=22):
    """
    Check/add hosts to the ``~/.ssh/known_hosts`` file.

    + hostname: hostname that should have a key in ``known_hosts``
    + force: if the key already exists, remove and rescan

    **Example:**

    .. code:: python

        from pyinfra.operations import ssh
        ssh.keyscan(
            name="Set add server two to known_hosts on one",
            hostname="two.example.com",
        )
    """

    homedir = host.get_fact(Home)

    yield from files.directory._inner(
        f"{homedir}/.ssh",
        mode=700,
    )

    hostname_present = host.get_fact(
        FindInFile,
        path=f"{homedir}/.ssh/known_hosts",
        pattern=hostname,
    )

    homedir = str(homedir)

    known_hosts = StringCommand(QuoteString(homedir), "/.ssh/known_hosts", _separator="")
    keyscan_command = StringCommand(
        "ssh-keyscan", "-p", str(port), QuoteString(hostname), ">>", known_hosts
    )

    if not hostname_present:
        yield keyscan_command

    elif force:
        yield StringCommand("ssh-keygen", "-R", QuoteString(hostname))
        yield keyscan_command

    else:
        host.noop(f"host key for {hostname} already exists")


@operation(is_idempotent=False)
def command(hostname: str, command: str, user: str | None = None, port=22):
    """
    Execute commands on other servers over SSH.

    + hostname: the hostname to connect to
    + command: the command to execute
    + user: connect with this user
    + port: connect to this port

    **Example:**

    .. code:: python

        ssh.command(
            name="Create file by running echo from host one to host two",
            hostname="two.example.com",
            command="echo 'one was here' > /tmp/one.txt",
            user="vagrant",
        )
    """

    connection_target = hostname
    if user:
        connection_target = "@".join((user, hostname))

    yield StringCommand(
        "ssh", "-p", str(port), QuoteString(connection_target), QuoteString(command)
    )


@operation(is_idempotent=False)
def upload(
    hostname: str,
    filename: str,
    remote_filename: str | None = None,
    port=22,
    user: str | None = None,
    use_remote_sudo=False,
    ssh_keyscan=False,
):
    """
    Upload files to other servers using ``scp``.

    + hostname: hostname to upload to
    + filename: file to upload
    + remote_filename: where to upload the file to (defaults to ``filename``)
    + port: connect to this port
    + user: connect with this user
    + use_remote_sudo: upload to a temporary location and move using sudo
    + ssh_keyscan: execute ``ssh.keyscan`` before uploading the file
    """

    remote_filename = remote_filename or filename

    # Figure out where we're connecting (host or user@host)
    connection_target = hostname
    if user:
        connection_target = "@".join((user, hostname))

    if ssh_keyscan:
        yield from keyscan._inner(hostname)

    # If we're not using sudo on the remote side, just scp the file over
    if not use_remote_sudo:
        scp_target = StringCommand(
            QuoteString(connection_target), ":", QuoteString(remote_filename), _separator=""
        )
        yield StringCommand("scp", "-P", str(port), QuoteString(filename), scp_target)

    else:
        # Otherwise - we need a temporary location for the file
        temp_remote_filename = host.get_temp_filename()

        # scp it to the temporary location
        scp_target = StringCommand(
            QuoteString(connection_target), ":", QuoteString(temp_remote_filename), _separator=""
        )
        yield StringCommand("scp", "-P", str(port), QuoteString(filename), scp_target)

        # And sudo to move it
        yield from command._inner(
            hostname=hostname,
            command=StringCommand(
                "sudo", "mv", QuoteString(temp_remote_filename), QuoteString(remote_filename)
            ).get_raw_value(),
            port=port,
            user=user,
        )


@operation()
def download(
    hostname: str,
    filename: str,
    local_filename: str | None = None,
    force=False,
    port=22,
    user: str | None = None,
    ssh_keyscan=False,
):
    """
    Download files from other servers using ``scp``.

    + hostname: hostname to upload to
    + filename: file to download
    + local_filename: where to download the file to (defaults to ``filename``)
    + force: always download the file, even if present locally
    + port: connect to this port
    + user: connect with this user
    + ssh_keyscan: execute ``ssh.keyscan`` before uploading the file
    """

    local_filename = local_filename or filename

    # Get local file info
    local_file_info = host.get_fact(File, path=local_filename)

    # Local file exists but isn't a file?
    if local_file_info is False:
        raise OperationError(
            f"Local destination {local_filename} already exists and is not a file",
        )

    # If the local file exists and we're not forcing a re-download, no-op
    if local_file_info and not force:
        host.noop(f"file {filename} is already downloaded")
        return

    # Figure out where we're connecting (host or user@host)
    connection_target = hostname
    if user:
        connection_target = "@".join((user, hostname))

    if ssh_keyscan:
        yield from keyscan._inner(hostname)

    # Download the file with scp
    scp_source = StringCommand(
        QuoteString(connection_target), ":", QuoteString(filename), _separator=""
    )
    yield StringCommand("scp", "-P", str(port), scp_source, QuoteString(local_filename))
