from __future__ import unicode_literals

from subprocess import PIPE, Popen

from pyinfra import logger
from pyinfra.api.util import make_command, read_buffer


def connect(state, host, **kwargs):
    return True


def run_shell_command(
    state, host, command,
    sudo=False, sudo_user=None, su_user=None, preserve_sudo_env=False,
    get_pty=False, env=None, timeout=None, print_output=False,
):
    command = make_command(
        command,
        env=env,
        sudo=sudo,
        sudo_user=sudo_user,
        su_user=su_user,
        preserve_sudo_env=preserve_sudo_env,
    )

    logger.debug('--> Running command on localhost: {0}'.format(command))

    print_prefix = host.print_prefix

    if print_output:
        print('{0}>>> {1}'.format(print_prefix, command))

    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)

    stdout = read_buffer(
        process.stdout,
        print_output=state.print_output,
        print_func=lambda line: '{0}{1}'.format(print_prefix, line),
    )

    stderr = read_buffer(
        process.stderr,
        print_output=state.print_output,
        print_func=lambda line: '{0}{1}'.format(print_prefix, line),
    )

    # Get & check result
    result = process.wait()

    # Close any open file descriptor
    process.stdout.close()

    return result == 0, stdout, stderr


def put_file(
    state, host, file_io, remote_file,
    sudo=False, sudo_user=None, su_user=None, print_output=False,
):
    with open(remote_file, 'w') as f:
        f.write(file_io.read())
