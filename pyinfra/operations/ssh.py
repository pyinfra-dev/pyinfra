'''
Execute commands and up/download files *from* the remote host.

Eg: ``pyinfra -> inventory-host.net <-> another-host.net``
'''

from pyinfra.api import operation, OperationError

from . import files


@operation
def keyscan(hostname, force=False, state=None, host=None):
    '''
    Check/add hosts to the ``~/.ssh/known_hosts`` file.

    + hostname: hostname that should have a key in ``known_hosts``
    + force: if the key already exists, remove and rescan

    Example:

    .. code:: python

        ssh.keyscan(
            name='Set add server two to known_hosts on one',
            hostname='two.example.com',
        )
    '''

    yield files.directory(
        '~/.ssh',
        mode=700,
        state=state,
        host=host,
    )

    hostname_present = host.fact.find_in_file(
        '~/.ssh/known_hosts',
        hostname,
    )

    keyscan_command = 'ssh-keyscan {0} >> ~/.ssh/known_hosts'.format(hostname)

    if not hostname_present:
        yield keyscan_command

    elif force:
        yield 'ssh-keygen -R {0}'.format(hostname)
        yield keyscan_command


@operation
def command(hostname, command, ssh_user=None, state=None, host=None):
    '''
    Execute commands on other servers over SSH.

    + hostname: the hostname to connect to
    + command: the command to execute
    + ssh_user: connect with this user

    Example:

    .. code:: python

        ssh.command(
            name='Create file by running echo from host one to host two',
            hostname='two.example.com',
            command='echo "one was here" > /tmp/one.txt',
            ssh_user='vagrant',
        )
    '''

    connection_target = hostname
    if ssh_user:
        connection_target = '@'.join((ssh_user, hostname))

    yield 'ssh {0} "{1}"'.format(connection_target, command)


@operation
def upload(
    hostname, filename,
    remote_filename=None, use_remote_sudo=False,
    ssh_keyscan=False, ssh_user=None,
    state=None, host=None,
):
    '''
    Upload files to other servers using ``scp``.

    + hostname: hostname to upload to
    + filename: file to upload
    + remote_filename: where to upload the file to (defaults to ``filename``)
    + use_remote_sudo: upload to a temporary location and move using sudo
    + ssh_keyscan: execute ``ssh.keyscan`` before uploading the file
    + ssh_user: connect with this user
    '''

    remote_filename = remote_filename or filename

    # Figure out where we're connecting (host or user@host)
    connection_target = hostname
    if ssh_user:
        connection_target = '@'.join((ssh_user, hostname))

    if ssh_keyscan:
        yield keyscan(hostname, state=state, host=host)

    # If we're not using sudo on the remote side, just scp the file over
    if not use_remote_sudo:
        yield 'scp {0} {1}:{2}'.format(filename, connection_target, remote_filename)

    else:
        # Otherwise - we need a temporary location for the file
        temp_remote_filename = state.get_temp_filename()

        # scp it to the temporary location
        upload_cmd = 'scp {0} {1}:{2}'.format(
            filename, connection_target, temp_remote_filename,
        )

        yield upload_cmd

        # And sudo sudo to move it
        yield command(
            hostname=connection_target,
            command='sudo mv {0} {1}'.format(temp_remote_filename, remote_filename),
            state=state,
            host=host,
        )


@operation
def download(
    hostname, filename,
    local_filename=None, force=False,
    ssh_keyscan=False, ssh_user=None,
    state=None, host=None,
):
    '''
    Download files from other servers using ``scp``.

    + hostname: hostname to upload to
    + filename: file to download
    + local_filename: where to download the file to (defaults to ``filename``)
    + force: always download the file, even if present locally
    + ssh_keyscan: execute ``ssh.keyscan`` before uploading the file
    + ssh_user: connect with this user
    '''

    local_filename = local_filename or filename

    # Get local file info
    local_file_info = host.fact.file(local_filename)

    # Local file exists but isn't a file?
    if local_file_info is False:
        raise OperationError(
            'Local destination {0} already exists and is not a file'.format(
                local_filename,
            ),
        )

    # If the local file exists and we're not forcing a re-download, no-op
    if local_file_info and not force:
        return

    # Figure out where we're connecting (host or user@host)
    connection_target = hostname
    if ssh_user:
        connection_target = '@'.join((ssh_user, hostname))

    if ssh_keyscan:
        yield keyscan(hostname, state=state, host=host)

    # Download the file with scp
    yield 'scp {0}:{1} {2}'.format(connection_target, filename, local_filename)
