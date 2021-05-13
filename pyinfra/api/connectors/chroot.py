import os

from tempfile import mkstemp

import click
import six

from pyinfra import local, logger
from pyinfra.api import QuoteString, StringCommand
from pyinfra.api.exceptions import ConnectError, InventoryError, PyinfraError
from pyinfra.api.util import get_file_io, memoize
from pyinfra.progress import progress_spinner

from .local import run_shell_command as run_local_shell_command
from .util import get_sudo_password, make_unix_command


@memoize
def show_warning():
    logger.warning('The @chroot connector is in beta!')


def make_names_data(directory=None):
    if not directory:
        raise InventoryError('No directory provided!')

    show_warning()

    yield '@chroot/{0}'.format(directory), {
        'chroot_directory': '/{0}'.format(directory.lstrip('/')),
    }, ['@chroot']


def connect(state, host):
    chroot_directory = host.data.chroot_directory

    try:
        with progress_spinner({'chroot run'}):
            local.shell(
                'chroot {0} ls'.format(chroot_directory), splitlines=True,
            )
    except PyinfraError as e:
        raise ConnectError(e.args[0])

    host.host_data['chroot_directory'] = chroot_directory
    return True


def run_shell_command(
    state,
    host,
    command,
    get_pty=False,
    timeout=None,
    stdin=None,
    success_exit_codes=None,
    print_output=False,
    print_input=False,
    return_combined_output=False,
    use_sudo_password=False,
    **command_kwargs
):

    if use_sudo_password:
        command_kwargs['use_sudo_password'] = get_sudo_password(
            state,
            host,
            use_sudo_password,
            run_shell_command=run_shell_command,
            put_file=put_file,
        )

    chroot_directory = host.host_data['chroot_directory']

    command = make_unix_command(command, state=state, **command_kwargs)
    command = QuoteString(command)

    logger.debug(
        '--> Running chroot command on ({0}):{1}'.format(
            chroot_directory, command,
        ),
    )

    chroot_command = StringCommand(
        'chroot', chroot_directory,
        'sh', '-c', command,
    )

    return run_local_shell_command(
        state,
        host,
        chroot_command,
        timeout=timeout,
        stdin=stdin,
        success_exit_codes=success_exit_codes,
        print_output=print_output,
        print_input=print_input,
        return_combined_output=return_combined_output,
    )


def put_file(
    state,
    host,
    filename_or_io,
    remote_filename,
    print_output=False,
    print_input=False,
    **kwargs  # ignored (sudo/etc)
):

    _, temp_filename = mkstemp()

    try:
        # Load our file or IO object and write it to the temporary file
        with get_file_io(filename_or_io) as file_io:
            with open(temp_filename, 'wb') as temp_f:
                data = file_io.read()

                if isinstance(data, six.text_type):
                    data = data.encode()

                temp_f.write(data)

        chroot_directory = host.host_data['chroot_directory']

        chroot_command = 'cp {0} {1}/{2}'.format(
            temp_filename, chroot_directory, remote_filename,
        )

        status, _, stderr = run_local_shell_command(
            state,
            host,
            chroot_command,
            print_output=print_output,
            print_input=print_input,
        )
    finally:
        os.remove(temp_filename)

    if not status:
        raise IOError('\n'.join(stderr))

    if print_output:
        click.echo(
            '{0}file uploaded to chroot: {1}'.format(
                host.print_prefix, remote_filename,
            ),
            err=True,
        )

    return status


def get_file(
    state,
    host,
    remote_filename,
    filename_or_io,
    print_output=False,
    print_input=False,
    **kwargs  # ignored (sudo/etc)
):

    _, temp_filename = mkstemp()

    try:
        chroot_directory = host.host_data['chroot_directory']
        chroot_command = 'cp {0}/{1} {2}'.format(
            chroot_directory, remote_filename, temp_filename,
        )

        status, _, stderr = run_local_shell_command(
            state,
            host,
            chroot_command,
            print_output=print_output,
            print_input=print_input,
        )

        # Load the temporary file and write it to our file or IO object
        with open(temp_filename) as temp_f:
            with get_file_io(filename_or_io, 'wb') as file_io:
                data = temp_f.read()

                if isinstance(data, six.text_type):
                    data = data.encode()

                file_io.write(data)
    finally:
        os.remove(temp_filename)

    if not status:
        raise IOError('\n'.join(stderr))

    if print_output:
        click.echo(
            '{0}file downloaded from chroot: {1}'.format(
                host.print_prefix, remote_filename,
            ),
            err=True,
        )

    return status


EXECUTION_CONNECTOR = True
