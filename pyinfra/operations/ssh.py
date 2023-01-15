"""
Execute commands and up/download files *from* the remote host.

Eg: ``pyinfra -> inventory-host.net <-> another-host.net``
"""

import shlex

from pyinfra import host, state
from pyinfra.api import OperationError, operation
from pyinfra.facts.files import File, FindInFile
from pyinfra.facts.server import Home

from . import files


@operation
def keyscan(hostname, force=False, port=22):
    """
    Check/add hosts to the ``~/.ssh/known_hosts`` file.

    + hostname: hostname that should have a key in ``known_hosts``
    + force: if the key already exists, remove and rescan

    **Example:**

    .. code:: python

        ssh.keyscan(
            name="Set add server two to known_hosts on one",
            hostname="two.example.com",
        )
    """

    homedir = host.get_fact(Home)

    yield from files.directory(
        "{0}/.ssh".format(homedir),
        mode=700,
    )

    hostname_present = host.get_fact(
        FindInFile,
        path="{0}/.ssh/known_hosts".format(homedir),
        pattern=hostname,
    )

    did_keyscan = False
    keyscan_command = "ssh-keyscan -p {0} {1} >> {2}/.ssh/known_hosts".format(
        port,
        hostname,
        homedir,
    )

    if not hostname_present:
        yield keyscan_command
        did_keyscan = True

    elif force:
        yield "ssh-keygen -R {0}".format(hostname)
        yield keyscan_command
        did_keyscan = True

    else:
        host.noop("host key for {0} already exists".format(hostname))

    if did_keyscan:
        host.create_fact(
            FindInFile,
            kwargs={"path": "{0}/.ssh/known_hosts".format(homedir), "pattern": hostname},
            data=["{0} unknown unknown".format(hostname)],
        )


@operation(is_idempotent=False)
def command(hostname, command, user=None, port=22):
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

    command = shlex.quote(command)

    connection_target = hostname
    if user:
        connection_target = "@".join((user, hostname))

    yield "ssh -p {0} {1} {2}".format(port, connection_target, command)


@operation(is_idempotent=False)
def upload(
    hostname,
    filename,
    remote_filename=None,
    port=22,
    user=None,
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
        yield from keyscan(hostname)

    # If we're not using sudo on the remote side, just scp the file over
    if not use_remote_sudo:
        yield "scp -P {0} {1} {2}:{3}".format(
            port,
            filename,
            connection_target,
            remote_filename,
        )

    else:
        # Otherwise - we need a temporary location for the file
        temp_remote_filename = state.get_temp_filename()

        # scp it to the temporary location
        upload_cmd = "scp -P {0} {1} {2}:{3}".format(
            port,
            filename,
            connection_target,
            temp_remote_filename,
        )

        yield upload_cmd

        # And sudo sudo to move it
        yield from command(
            hostname=hostname,
            command="sudo mv {0} {1}".format(temp_remote_filename, remote_filename),
            port=port,
            user=user,
        )


@operation
def download(
    hostname,
    filename,
    local_filename=None,
    force=False,
    port=22,
    user=None,
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
            "Local destination {0} already exists and is not a file".format(
                local_filename,
            ),
        )

    # If the local file exists and we're not forcing a re-download, no-op
    if local_file_info and not force:
        host.noop("file {0} is already downloaded".format(filename))
        return

    # Figure out where we're connecting (host or user@host)
    connection_target = hostname
    if user:
        connection_target = "@".join((user, hostname))

    if ssh_keyscan:
        yield from keyscan(hostname)

    # Download the file with scp
    yield "scp -P {0} {1}:{2} {3}".format(
        port,
        connection_target,
        filename,
        local_filename,
    )
    host.create_fact(
        File,
        kwargs={"path": local_filename},
        data={"mode": None, "group": None, "user": user, "mtime": None},
    )
