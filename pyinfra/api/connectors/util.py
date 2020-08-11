from __future__ import unicode_literals

import re

from getpass import getpass
from socket import timeout as timeout_error
from subprocess import PIPE, Popen

import click
import gevent
import six

from gevent.queue import Queue
from six.moves import shlex_quote

from pyinfra import logger
from pyinfra.api import Config, MaskString, QuoteString, StringCommand
from pyinfra.api.util import read_buffer

SUDO_ASKPASS_ENV_VAR = 'PYINFRA_SUDO_PASSWORD'
SUDO_ASKPASS_EXE_FILENAME = 'pyinfra-sudo-askpass'
SUDO_ASKPASS_EXE = six.StringIO('''#!/bin/sh
echo ${0}
'''.format(SUDO_ASKPASS_ENV_VAR))

UNIX_PATH_SPACE_REGEX = re.compile(r'([^\\]) ')


def escape_unix_path(path):
    '''
    Escape unescaped spaces in a (unix) path.
    '''

    return UNIX_PATH_SPACE_REGEX.sub(r'\1\\ ', path)


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


def get_sudo_password(state, host, use_sudo_password, run_shell_command, put_file):
    sudo_askpass_uploaded = host.connector_data.get('sudo_askpass_uploaded', False)
    if not sudo_askpass_uploaded:
        put_file(state, host, SUDO_ASKPASS_EXE, SUDO_ASKPASS_EXE_FILENAME)
        run_shell_command(state, host, 'chmod +x {0}'.format(SUDO_ASKPASS_EXE_FILENAME))
        host.connector_data['sudo_askpass_uploaded'] = True

    if use_sudo_password is True:
        sudo_password = host.connector_data.get('sudo_password')
        if not sudo_password:
            sudo_password = getpass('{0}sudo password: '.format(host.print_prefix))
            host.connector_data['sudo_password'] = sudo_password
    else:
        sudo_password = use_sudo_password

    return (SUDO_ASKPASS_EXE_FILENAME, sudo_password)


def make_unix_command(
    command,
    env=None,
    su_user=Config.SU_USER,
    use_su_login=Config.USE_SU_LOGIN,
    sudo=Config.SUDO,
    sudo_user=Config.SUDO_USER,
    use_sudo_login=Config.USE_SUDO_LOGIN,
    use_sudo_password=Config.USE_SUDO_PASSWORD,
    preserve_sudo_env=Config.PRESERVE_SUDO_ENV,
    shell_executable=Config.SHELL,
    raw=True,
):
    '''
    Builds a shell command with various kwargs.
    '''

    if shell_executable is None or not isinstance(shell_executable, six.string_types):
        shell_executable = 'sh'

    command_bits = []

    # Use sudo (w/user?)
    if sudo:
        if use_sudo_password:
            askpass_filename, sudo_password = use_sudo_password
            command_bits.extend([
                'env',
                'SUDO_ASKPASS={0}'.format(askpass_filename),
                MaskString('{0}={1}'.format(SUDO_ASKPASS_ENV_VAR, sudo_password)),
            ])

        sudo_bits = ['sudo', '-H']

        if use_sudo_password:
            sudo_bits.extend(['-A', '-k'])  # use askpass, disable cache
        else:
            sudo_bits.append('-n')  # disable prompt/interactivity

        if use_sudo_login:
            sudo_bits.append('-i')

        if preserve_sudo_env:
            sudo_bits.append('-E')

        if sudo_user:
            sudo_bits.extend(('-u', sudo_user))

        command_bits.extend(sudo_bits)

    # Switch user with su
    if su_user:
        su_bits = ['su']

        if use_su_login:
            su_bits.append('-l')

        # note `which <shell>` usage here - su requires an absolute path
        command_bits.extend(su_bits)
        command_bits.extend([su_user, '-s', '`which {0}`'.format(shell_executable), '-c'])

    else:
        # Otherwise just sh wrap the command
        command_bits.extend([shell_executable, '-c'])

    #
    # OK, now parse the command!
    #

    if isinstance(command, six.binary_type):
        command = command.decode('utf-8')

    # Use env & build our actual command
    if env:
        env_string = ' '.join([
            '{0}={1}'.format(key, value)
            for key, value in six.iteritems(env)
        ])
        command = StringCommand('env', env_string, command)

    # Quote the command as a string
    command = QuoteString(command)
    command_bits.append(command)

    return StringCommand(*command_bits)
    # return command.get_raw_value(), command.get_masked_value()


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
