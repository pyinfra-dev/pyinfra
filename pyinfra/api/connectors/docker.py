import os

from tempfile import mkstemp

import click
import six

import pyinfra

from pyinfra import local, logger
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import get_file_io
from pyinfra.progress import progress_spinner

from .local import run_shell_command as run_local_shell_command


def make_names_data(image=None):
    if not image:
        raise InventoryError('No docker base image provided!')

    # Save the image as the hostname, no data, @docker group
    yield image, {}, ['@docker']


def connect(state, host, for_fact=None):
    if 'docker_container_id' in host.host_data:  # user can provide a docker_container_id
        return True

    with progress_spinner({'docker run'}):
        container_id = local.shell(
            'docker run -d {0} sleep 10000'.format(host.name),
            splitlines=True,
        )[-1]  # last line is the container ID

    host.host_data['docker_container_id'] = container_id
    return True


def disconnect(state, host):
    if not pyinfra.is_cli:
        return

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
    timeout=None, print_output=False,
    **kwargs  # ignored (sudo/etc)
):
    container_id = host.host_data['docker_container_id']
    docker_command = 'docker exec {0} sh -c "{1}"'.format(container_id, command)

    return run_local_shell_command(
        state, host, docker_command,
        timeout=timeout,
        print_output=print_output,
    )


def put_file(
    state, host, filename_or_io, remote_filename,
    print_output=False,
    **kwargs  # ignored (sudo/etc)
):
    _, temp_filename = mkstemp()

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
    )

    if temp_filename:
        os.remove(temp_filename)

    if not status:
        raise IOError('\n'.join(stderr))

    if print_output:
        print('{0}file copied: {1}'.format(host.print_prefix, remote_filename))

    return status
