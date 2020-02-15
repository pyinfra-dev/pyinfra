from socket import timeout as timeout_error
from subprocess import PIPE, Popen

import click
import gevent
import six

from gevent.queue import Queue
from six.moves import shlex_quote

from pyinfra import logger
from pyinfra.api import Config
from pyinfra.api.util import read_buffer


def run_local_process(
    command,
    stdin=None,
    timeout=None,
    print_output=False,
    print_prefix=None,
):
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, stdin=PIPE)

    if stdin:
        write_stdin(stdin, process.stdin)

    combined_output = read_buffers_into_queue(
        process.stdout,
        process.stderr,
        timeout=timeout,
        print_output=print_output,
        print_prefix=print_prefix,
    )

    logger.debug('--> Waiting for exit status...')
    process.wait()
    logger.debug('--> Command exit status: {0}'.format(process.returncode))

    # Close any open file descriptors
    process.stdout.close()
    process.stderr.close()

    return process.returncode, combined_output


def read_buffers_into_queue(
    stdout_buffer, stderr_buffer, timeout, print_output, print_prefix,
):
    output_queue = Queue()

    # Iterate through outputs to get an exit status and generate desired list
    # output, done in two greenlets so stdout isn't printed before stderr. Not
    # attached to state.pool to avoid blocking it with 2x n-hosts greenlets.
    stdout_reader = gevent.spawn(
        read_buffer,
        'stdout',
        stdout_buffer,
        output_queue,
        print_output=print_output,
        print_func=lambda line: '{0}{1}'.format(print_prefix, line),
    )
    stderr_reader = gevent.spawn(
        read_buffer,
        'stderr',
        stderr_buffer,
        output_queue,
        print_output=print_output,
        print_func=lambda line: '{0}{1}'.format(
            print_prefix, click.style(line, 'red'),
        ),
    )

    # Wait on output, with our timeout (or None)
    greenlets = gevent.wait((stdout_reader, stderr_reader), timeout=timeout)

    # Timeout doesn't raise an exception, but gevent.wait returns the greenlets
    # which did complete. So if both haven't completed, we kill them and fail
    # with a timeout.
    if len(greenlets) != 2:
        stdout_reader.kill()
        stderr_reader.kill()

        raise timeout_error()

    return list(output_queue.queue)


def split_combined_output(combined_output):
    stdout = []
    stderr = []

    for type_, line in combined_output:
        if type_ == 'stdout':
            stdout.append(line)
        elif type_ == 'stderr':
            stderr.append(line)
        else:  # pragma: no cover
            raise ValueError('Incorrect output line type: {0}'.format(type_))

    return stdout, stderr


def write_stdin(stdin, buffer):
    if not isinstance(stdin, (list, tuple)):
        stdin = [stdin]

    for line in stdin:
        if not line.endswith('\n'):
            line = '{0}\n'.format(line)
        line = line.encode()
        buffer.write(line)
    buffer.close()


def make_unix_command(
    command,
    env=None,
    su_user=Config.SU_USER,
    use_su_login=Config.USE_SU_LOGIN,
    sudo=Config.SUDO,
    sudo_user=Config.SUDO_USER,
    use_sudo_login=Config.USE_SUDO_LOGIN,
    preserve_sudo_env=Config.PRESERVE_SUDO_ENV,
    shell_executable=Config.SHELL,
):
    '''
    Builds a shell command with various kwargs.
    '''

    if shell_executable is None or not isinstance(shell_executable, six.string_types):
        shell_executable = 'sh'

    debug_meta = {}

    for key, value in (
        ('shell_executable', shell_executable),
        ('sudo', sudo),
        ('sudo_user', sudo_user),
        ('su_user', su_user),
        ('env', env),
    ):
        if value:
            debug_meta[key] = value

    logger.debug('Building command ({0}): {1}'.format(' '.join(
        '{0}: {1}'.format(key, value)
        for key, value in six.iteritems(debug_meta)
    ), command))

    # Use env & build our actual command
    if env:
        env_string = ' '.join([
            '{0}={1}'.format(key, value)
            for key, value in six.iteritems(env)
        ])
        command = 'export {0}; {1}'.format(env_string, command)

    # Quote the command as a string
    command = shlex_quote(command)

    # Switch user with su
    if su_user:
        su_bits = ['su']

        if use_su_login:
            su_bits.append('-l')

        # note `which <shell>` usage here - su requires an absolute path
        command = '{0} {1} -s `which {2}` -c {3}'.format(
            ' '.join(su_bits), su_user, shell_executable, command,
        )

    else:
        # Otherwise just sh wrap the command
        command = '{0} -c {1}'.format(shell_executable, command)

    # Use sudo (w/user?)
    if sudo:
        sudo_bits = ['sudo', '-S', '-H', '-n']

        if use_sudo_login:
            sudo_bits.append('-i')

        if preserve_sudo_env:
            sudo_bits.append('-E')

        if sudo_user:
            sudo_bits.extend(('-u', sudo_user))

        command = '{0} {1}'.format(' '.join(sudo_bits), command)

    return command


def make_win_command(
    command,
    env=None,
    shell_executable=Config.SHELL,
):
    '''
    Builds a windows command with various kwargs.
    '''

    debug_meta = {}

    for key, value in (
        ('shell_executable', shell_executable),
        ('env', env),
    ):
        if value:
            debug_meta[key] = value

    logger.debug('Building command ({0}): {1}'.format(' '.join(
        '{0}: {1}'.format(key, value)
        for key, value in six.iteritems(debug_meta)
    ), command))

    # Use env & build our actual command
    if env:
        env_string = ' '.join([
            '{0}={1}'.format(key, value)
            for key, value in six.iteritems(env)
        ])
        command = 'export {0}; {1}'.format(env_string, command)

    # Quote the command as a string
    command = shlex_quote(command)

    command = '{0}'.format(command)

    return command
