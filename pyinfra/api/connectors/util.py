from __future__ import unicode_literals

from getpass import getpass
from socket import timeout as timeout_error
from subprocess import PIPE, Popen

import click
import gevent
import six

from gevent.queue import Queue
from six.moves import shlex_quote

from pyinfra import logger
from pyinfra.api import MaskString, QuoteString, StringCommand
from pyinfra.api.util import memoize

SUDO_ASKPASS_ENV_VAR = 'PYINFRA_SUDO_PASSWORD'
SUDO_ASKPASS_EXE_FILENAME = 'pyinfra-sudo-askpass'


def get_sudo_askpass_exe():
    return six.StringIO('''#!/bin/sh
echo ${0}
'''.format(SUDO_ASKPASS_ENV_VAR))


def read_buffer(type_, io, output_queue, print_output=False, print_func=None):
    '''
    Reads a file-like buffer object into lines and optionally prints the output.
    '''

    def _print(line):
        if print_func:
            line = print_func(line)

        if six.PY2:  # Python2 must print unicode as bytes (encoded)
            line = line.encode('utf-8')

        click.echo(line, err=True)

    for line in io:
        # Handle local Popen shells returning list of bytes, not strings
        if not isinstance(line, six.text_type):
            line = line.decode('utf-8')

        line = line.rstrip('\n')
        output_queue.put((type_, line))

        if print_output:
            _print(line)


def execute_command_with_sudo_retry(host, command_kwargs, execute_command):
    return_code, combined_output = execute_command()

    if return_code != 0 and combined_output:
        last_line = combined_output[-1][1]
        if last_line == 'sudo: a password is required':
            command_kwargs['use_sudo_password'] = True  # ask for the password
            return_code, combined_output = execute_command()

    return return_code, combined_output


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


def _get_sudo_password(host, use_sudo_password):
    sudo_askpass_uploaded = host.connector_data.get('sudo_askpass_uploaded', False)
    if not sudo_askpass_uploaded:
        host.put_file(get_sudo_askpass_exe(), SUDO_ASKPASS_EXE_FILENAME)
        host.run_shell_command('chmod +x {0}'.format(SUDO_ASKPASS_EXE_FILENAME))
        host.connector_data['sudo_askpass_uploaded'] = True

    if use_sudo_password is True:
        sudo_password = host.connector_data.get('sudo_password')
        if not sudo_password:
            sudo_password = getpass('{0}sudo password: '.format(host.print_prefix))
            host.connector_data['sudo_password'] = sudo_password
        sudo_password = sudo_password
    elif callable(use_sudo_password):
        sudo_password = use_sudo_password()
    else:
        # FIXME
        # This is a workaround for an issue where use_sudo_password is defined as
        # a string on host.data and differs between hosts. The use_sudo_password
        # passed into this function may originate from a different host (at fact
        # gathering stage from state.current_op_kwargs).
        sudo_password = host.data.use_sudo_password
        if not isinstance(sudo_password, six.text_type):
            sudo_password = use_sudo_password

    return shlex_quote(sudo_password)


def remove_any_sudo_askpass_file(host):
    sudo_askpass_uploaded = host.connector_data.get('sudo_askpass_uploaded', False)
    if sudo_askpass_uploaded:
        host.run_shell_command('rm -f {0}'.format(SUDO_ASKPASS_EXE_FILENAME))
        host.connector_data['sudo_askpass_uploaded'] = False


@memoize
def _show_use_su_login_warning():
    logger.warning((
        'Using `use_su_login` may not work: '
        'some systems (MacOS, OpenBSD) ignore the flag when executing a command, '
        'use `sudo` + `use_sudo_login` instead.'
    ))


# TODO (v2): possibly raise an error for invalid arguments
def _warn_invalid_auth_args(args, requires_key, invalid_keys):
    for key in invalid_keys:
        if args.get(key):
            logger.warning((
                'Invalid auth argument: cannot use `{0}` without `{1}`.'
            ).format(key, requires_key))


def make_unix_command_for_host(state, host, *command_args, **command_kwargs):
    if not command_kwargs.get('doas') and not state.config.DOAS:
        _warn_invalid_auth_args(command_kwargs, 'doas', ('doas_user',))

    # If both sudo arg and config sudo are false, warn if any of the other sudo
    # arguments are present as they will be ignored.
    if not command_kwargs.get('sudo') and not state.config.SUDO:
        _warn_invalid_auth_args(
            command_kwargs,
            'sudo',
            ('use_sudo_password', 'use_sudo_login', 'preserve_sudo_env', 'sudo_user'),
        )

    if not command_kwargs.get('su_user') and not state.config.SU_USER:
        _warn_invalid_auth_args(
            command_kwargs,
            'su_user',
            ('use_su_login', 'preserve_su_env', 'su_shell'),
        )

    use_sudo_password = command_kwargs.pop('use_sudo_password', None)
    if use_sudo_password:
        command_kwargs['sudo_password'] = _get_sudo_password(host, use_sudo_password)

    return make_unix_command(*command_args, **command_kwargs)


def make_unix_command(
    command,
    env=None,
    chdir=None,
    shell_executable='sh',
    # Su config
    su_user=None,
    use_su_login=False,
    su_shell=None,
    preserve_su_env=False,
    # Sudo config
    sudo=False,
    sudo_user=None,
    use_sudo_login=False,
    sudo_password=False,
    preserve_sudo_env=False,
    # Doas config
    doas=False,
    doas_user=None,
):
    '''
    Builds a shell command with various kwargs.
    '''

    if shell_executable is not None and not isinstance(shell_executable, six.string_types):
        shell_executable = 'sh'

    if isinstance(command, six.binary_type):
        command = command.decode('utf-8')

    if env:
        env_string = ' '.join([
            '{0}={1}'.format(key, value)
            for key, value in six.iteritems(env)
        ])
        command = StringCommand('export', env_string, '&&', command)

    if chdir:
        command = StringCommand('cd', chdir, '&&', command)

    command_bits = []

    if doas:
        command_bits.extend(['doas', '-n'])

        if doas_user:
            command_bits.extend(['-u', doas_user])

    if sudo_password:
        command_bits.extend([
            'env',
            'SUDO_ASKPASS={0}'.format(SUDO_ASKPASS_EXE_FILENAME),
            MaskString('{0}={1}'.format(SUDO_ASKPASS_ENV_VAR, sudo_password)),
        ])

    if sudo:
        command_bits.extend(['sudo', '-H'])

        if sudo_password:
            command_bits.extend(['-A', '-k'])  # use askpass, disable cache
        else:
            command_bits.append('-n')  # disable prompt/interactivity

        if use_sudo_login:
            command_bits.append('-i')

        if preserve_sudo_env:
            command_bits.append('-E')

        if sudo_user:
            command_bits.extend(('-u', sudo_user))

    if su_user:
        command_bits.append('su')

        if use_su_login:
            _show_use_su_login_warning()
            command_bits.append('-l')

        if preserve_su_env:
            command_bits.append('-m')

        if su_shell:
            command_bits.extend(['-s', '`which {0}`'.format(su_shell)])

        command_bits.extend([su_user, '-c'])

        if shell_executable is not None:
            # Quote the whole shell -c 'command' as BSD `su` does not have a shell option
            command_bits.append(
                QuoteString(StringCommand(shell_executable, '-c', QuoteString(command))),
            )
        else:
            command_bits.append(QuoteString(StringCommand(command)))
    else:
        if shell_executable is not None:
            command_bits.extend([shell_executable, '-c', QuoteString(command)])
        else:
            command_bits.extend([command])

    return StringCommand(*command_bits)


def make_win_command(command):
    '''
    Builds a windows command with various kwargs.
    '''

    # Quote the command as a string
    command = shlex_quote(str(command))
    command = '{0}'.format(command)

    return command
