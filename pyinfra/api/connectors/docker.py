import os

from tempfile import mkstemp

import click
import six

from six.moves import shlex_quote

from pyinfra import local, logger
from pyinfra.api.exceptions import ConnectError, InventoryError, PyinfraError
from pyinfra.api.util import get_file_io, memoize
from pyinfra.progress import progress_spinner

from .local import run_shell_command as run_local_shell_command


@memoize
def show_warning():
    logger.warning('The @docker connector is in beta!')


def make_names_data(image=None):
    if not image:
        raise InventoryError('No docker base image provided!')

    show_warning()

    # Save the image as the hostname, the image as data, @docker group
    yield '@docker/{0}'.format(image), {'docker_image': image}, ['@docker']


def connect(state, host, for_fact=None):
    if 'docker_container_id' in host.host_data:  # user can provide a docker_container_id
        return True

    try:
        with progress_spinner({'docker run'}):
            container_id = local.shell(
                'docker run -d {0} sleep 10000'.format(host.data.docker_image),
                splitlines=True,
            )[-1]  # last line is the container ID
    except PyinfraError as e:
        raise ConnectError(e.args[0])

    host.host_data['docker_container_id'] = container_id
    return True


def disconnect(state, host):
    container_id = host.host_data['docker_container_id'][:12]

    with progress_spinner({'docker commit'}):
        image_id = local.shell(
            'docker commit {0}'.format(container_id),
            splitlines=True,
        )[-1][7:19]  # last line is the image ID, get sha256:[XXXXXXXXXX]...

    with progress_spinner({'docker rm'}):
        local.shell(
            'docker rm -f {0}'.format(container_id),
        )

    logger.info('{0}docker build complete, image ID: {1}'.format(
        host.print_prefix, click.style(image_id, bold=True),
    ))


def run_shell_command(
    state, host, command,
    timeout=None,
    stdin=None,
    success_exit_codes=None,
    print_output=False,
    print_input=False,
    return_combined_output=False,
    **kwargs  # ignored (sudo/etc)
):
    container_id = host.host_data['docker_container_id']
    command = shlex_quote(command)
    docker_command = 'docker exec -i {0} sh -c {1}'.format(container_id, command)

    return run_local_shell_command(
        state, host, docker_command,
        timeout=timeout,
        stdin=stdin,
        success_exit_codes=success_exit_codes,
        print_output=print_output,
        print_input=print_input,
        return_combined_output=return_combined_output,
    )


def put_file(
    state, host, filename_or_io, remote_filename,
    print_output=False, print_input=False,
    **kwargs  # ignored (sudo/etc)
):
    '''
    Upload a file/IO object to the target Docker container by copying it to a
    temporary location and then uploading it into the container using ``docker cp``.
    '''

    _, temp_filename = mkstemp()

    try:
        # Load our file or IO object and write it to the temporary file
        with get_file_io(filename_or_io) as file_io:
            with open(temp_filename, 'wb') as temp_f:
                data = file_io.read()

                if isinstance(data, six.text_type):
                    data = data.encode()

                temp_f.write(data)

        docker_id = host.host_data['docker_container_id']
        docker_command = 'docker cp {0} {1}:{2}'.format(
            temp_filename,
            docker_id,
            remote_filename,
        )

        status, _, stderr = run_local_shell_command(
            state, host, docker_command,
            print_output=print_output,
            print_input=print_input,
        )
    finally:
        os.remove(temp_filename)

    if not status:
        raise IOError('\n'.join(stderr))

    if print_output:
        click.echo('{0}file uploaded to container: {1}'.format(
            host.print_prefix, remote_filename,
        ))

    return status


def get_file(
    state, host, remote_filename, filename_or_io,
    print_output=False, print_input=False,
    **kwargs  # ignored (sudo/etc)
):
    '''
    Download a file from the target Docker container by copying it to a temporary
    location and then reading that into our final file/IO object.
    '''

    _, temp_filename = mkstemp()

    try:
        docker_id = host.host_data['docker_container_id']
        docker_command = 'docker cp {0}:{1} {2}'.format(
            docker_id,
            remote_filename,
            temp_filename,
        )

        status, _, stderr = run_local_shell_command(
            state, host, docker_command,
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
        click.echo('{0}file downloaded from container: {1}'.format(
            host.print_prefix, remote_filename,
        ))

    return status
