import os

from tempfile import mkstemp

import click
import six

from pyinfra import logger
from pyinfra.api import QuoteString, StringCommand
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import get_file_io, memoize

from .local import run_shell_command as run_local_shell_command
from .util import make_unix_command, run_local_process, split_combined_output


@memoize
def show_warning():
    logger.warning('The @kubernetes connector is in beta!')


def make_names_data(pod=None):
    if not pod:
        raise InventoryError('No pod provided!')

    namespace = 'default'
    if '/' in pod:
        namespace, pod = pod.split('/', 2)

    show_warning()

    # Save the namespace and pod name as the hostname, @kubernetes group
    yield '@kubernetes/{0}/{1}'.format(namespace, pod), \
        {'namespace': namespace, 'pod': pod}, ['@kubernetes']


def connect(state, host, for_fact=None):
    return True


def disconnect(state, host):
    return True


def run_shell_command(
    state, host, command,
    get_pty=False,
    timeout=None,
    stdin=None,
    success_exit_codes=None,
    print_output=False,
    print_input=False,
    return_combined_output=False,
    **command_kwargs
):
    # Don't sudo/su, see docker connector.
    for key in ('sudo', 'su_user'):
        command_kwargs.pop(key, None)

    command = make_unix_command(command, **command_kwargs)
    command = QuoteString(command)

    kubectl_command = ['kubectl', 'exec', '-i']
    if get_pty:
        kubectl_command += ['-t']
    kubectl_command += ['-n', host.host_data['namespace']]
    if 'container' in host.host_data:
        kubectl_command += ['-c', host.host_data['container']]
    kubectl_command += [host.host_data['pod'], '--', 'sh', '-c', command]
    kubectl_command = StringCommand(*kubectl_command)

    return run_local_shell_command(
        state, host, kubectl_command,
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
    Upload a file/IO object to the target pod by copying it to a
    temporary location and then uploading it into the container using
    ``kubectl cp``.
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

        if 'container' in host.host_data:
            container = ['-c', host.host_data['container']]
        else:
            container = []

        kubectl_command = StringCommand(
            'kubectl', 'cp',
            temp_filename,
            '{0}/{1}:{2}'.format(host.host_data['namespace'],
                                 host.host_data['pod'],
                                 remote_filename),
            *container
        )

        status, _, stderr = run_local_shell_command(
            state, host, kubectl_command,
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
        ), err=True)

    return status


def get_file(
    state, host, remote_filename, filename_or_io,
    print_output=False, print_input=False,
    **kwargs  # ignored (sudo/etc)
):
    '''
    Download a file from the target pod by copying it to a temporary
    location and then reading that into our final file/IO object.
    '''

    _, temp_filename = mkstemp()

    try:
        if 'container' in host.host_data:
            container = ['-c', host.host_data['container']]
        else:
            container = []

        kubectl_command = StringCommand(
            'kubectl', 'cp',
            '{0}/{1}:{2}'.format(host.host_data['namespace'],
                                 host.host_data['pod'],
                                 remote_filename),
            temp_filename,
            *container
        )

        status, _, stderr = run_local_shell_command(
            state, host, kubectl_command,
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
        click.echo('{0}file downloaded from pod: {1}'.format(
            host.print_prefix, remote_filename,
        ), err=True)

    return status


def get_pods(selector, namespace='default', all_namespaces=False, container=None):

    command = ['kubectl', 'get', 'pods']
    if all_namespaces:
        command += ['-A']
    else:
        command += ['-n', namespace]
    command += ['-l', selector]
    command += [
        '--template',
        r'{{range .items}}'
        r'@kubernetes/{{.metadata.namespace}}/{{.metadata.name}}{{"\n"}}'
        r'{{end}}',
    ]

    return_code, combined_output = run_local_process(['"$@"', '-'] + command)
    stdout, stderr = split_combined_output(combined_output)

    if return_code == 0:
        data = {}
        if container:
            data['container'] = container
        return list(map(lambda s: (s, data), stdout))
    else:
        raise InventoryError('kubectl failed (status {0}): {1}'.
                             format(return_code, '\n'.join(stderr)))


EXECUTION_CONNECTOR = True
