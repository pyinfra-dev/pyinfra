'''
Execute commands and up/download files *from* the remote host.

Eg: ``pyinfra -> inventory-host.net <-> another-host.net``
'''

from six.moves import shlex_quote

from pyinfra import logger
from pyinfra.api import operation, OperationError
from pyinfra.facts.files import File, FindInFile

from . import files


@operation
def keyscan(hostname, force=False, port=22, state=None, host=None):
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

    hostname_present = host.get_fact(
        FindInFile,
        path='~/.ssh/known_hosts',
        pattern=hostname,
    )

    keyscan_command = 'ssh-keyscan -p {0} {1} >> ~/.ssh/known_hosts'.format(
        port, hostname,
    )

    if not hostname_present:
        yield keyscan_command

    elif force:
        yield 'ssh-keygen -R {0}'.format(hostname)
        yield keyscan_command

    else:
        host.noop('host key for {0} already exists'.format(hostname))


def _user_or_ssh_user(user, ssh_user):
    if ssh_user:
        logger.warning((
            'The `ssh_user` argument is deprecated in `ssh.*` operations, '
            'please use the `user` argument.'
        ))
    return user or ssh_user


@operation
def command(hostname, command, user=None, port=22, ssh_user=None, state=None, host=None):
    '''
    Execute commands on other servers over SSH.

    + hostname: the hostname to connect to
    + command: the command to execute
    + user: connect with this user
    + port: connect to this port

    Example:

    .. code:: python

        ssh.command(
            name='Create file by running echo from host one to host two',
            hostname='two.example.com',
            command='echo "one was here" > /tmp/one.txt',
            user='vagrant',
        )
    '''

    # TODO: remove this (ssh_user is a legacy arg)
    user = _user_or_ssh_user(user, ssh_user)

    command = shlex_quote(command)

    connection_target = hostname
    if user:
        connection_target = '@'.join((user, hostname))

    yield 'ssh -p {0} {1} {2}'.format(port, connection_target, command)


@operation
def upload(
    hostname, filename,
    remote_filename=None,
    port=22,
    user=None,
    use_remote_sudo=False,
    ssh_keyscan=False,
    ssh_user=None,
    state=None, host=None,
):
    '''
    Upload files to other servers using ``scp``.

    + hostname: hostname to upload to
    + filename: file to upload
    + remote_filename: where to upload the file to (defaults to ``filename``)
    + port: connect to this port
    + user: connect with this user
    + use_remote_sudo: upload to a temporary location and move using sudo
    + ssh_keyscan: execute ``ssh.keyscan`` before uploading the file
    '''

    remote_filename = remote_filename or filename

    # TODO: remove this (ssh_user is a legacy arg)
    user = _user_or_ssh_user(user, ssh_user)

    # Figure out where we're connecting (host or user@host)
    connection_target = hostname
    if user:
        connection_target = '@'.join((user, hostname))

    if ssh_keyscan:
        yield keyscan(hostname, state=state, host=host)

    # If we're not using sudo on the remote side, just scp the file over
    if not use_remote_sudo:
        yield 'scp -P {0} {1} {2}:{3}'.format(
            port, filename, connection_target, remote_filename,
        )

    else:
        # Otherwise - we need a temporary location for the file
        temp_remote_filename = state.get_temp_filename()

        # scp it to the temporary location
        upload_cmd = 'scp -P {0} {1} {2}:{3}'.format(
            port, filename, connection_target, temp_remote_filename,
        )

        yield upload_cmd

        # And sudo sudo to move it
        yield command(
            hostname=connection_target,
            command='sudo mv {0} {1}'.format(temp_remote_filename, remote_filename),
            port=port,
            user=user,
            state=state,
            host=host,
        )


@operation
def download(
    hostname, filename,
    local_filename=None,
    force=False,
    port=22,
    user=None,
    ssh_keyscan=False,
    ssh_user=None,
    state=None, host=None,
):
    '''
    Download files from other servers using ``scp``.

    + hostname: hostname to upload to
    + filename: file to download
    + local_filename: where to download the file to (defaults to ``filename``)
    + force: always download the file, even if present locally
    + port: connect to this port
    + user: connect with this user
    + ssh_keyscan: execute ``ssh.keyscan`` before uploading the file
    '''

    local_filename = local_filename or filename

    # TODO: remove this (ssh_user is a legacy arg)
    user = _user_or_ssh_user(user, ssh_user)

    # Get local file info
    local_file_info = host.get_fact(File, path=local_filename)

    # Local file exists but isn't a file?
    if local_file_info is False:
        raise OperationError(
            'Local destination {0} already exists and is not a file'.format(
                local_filename,
            ),
        )

    # If the local file exists and we're not forcing a re-download, no-op
    if local_file_info and not force:
        host.noop('file {0} is already downloaded'.format(filename))
        return

    # Figure out where we're connecting (host or user@host)
    connection_target = hostname
    if ssh_user:
        connection_target = '@'.join((ssh_user, hostname))

    if ssh_keyscan:
        yield keyscan(hostname, state=state, host=host)

    # Download the file with scp
    yield 'scp -P {0} {1}:{2} {3}'.format(
        port, connection_target, filename, local_filename,
    )
