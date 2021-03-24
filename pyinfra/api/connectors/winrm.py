from __future__ import print_function, unicode_literals

import click
import winrm

from pyinfra import logger
from pyinfra.api import Config
from pyinfra.api.exceptions import ConnectError, PyinfraError
from pyinfra.api.util import memoize

from .util import make_win_command


def _raise_connect_error(host, message, data):
    message = '{0} ({1})'.format(message, data)
    raise ConnectError(message)


@memoize
def show_warning():
    logger.warning('The @winrm connector is alpha!')


def _make_winrm_kwargs(state, host):
    kwargs = {
    }

    for key, value in (
        ('username', host.data.winrm_user),
        ('password', host.data.winrm_password),
        ('winrm_port', int(host.data.winrm_port or 0)),
        ('winrm_transport', host.data.winrm_transport or 'plaintext'),
        ('winrm_read_timeout_sec', host.data.winrm_read_timeout_sec or 30),
        ('winrm_operation_timeout_sec', host.data.winrm_operation_timeout_sec or 20),
    ):
        if value:
            kwargs[key] = value

    # FUTURE: add more auth
    # pywinrm supports: basic, certificate, ntlm, kerberos, plaintext, ssl, credssp
    # see https://github.com/diyan/pywinrm/blob/master/winrm/__init__.py#L12

    return kwargs


def make_names_data(hostname):

    show_warning()

    yield '@winrm/{0}'.format(hostname), {'winrm_hostname': hostname}, []


def connect(state, host):
    '''
    Connect to a single host. Returns the winrm Session if successful.
    '''

    kwargs = _make_winrm_kwargs(state, host)
    logger.debug('Connecting to: %s (%s)', host.name, kwargs)

    # Hostname can be provided via winrm config (alias), data, or the hosts name
    hostname = kwargs.pop(
        'hostname',
        host.data.winrm_hostname or host.name,
    )

    try:
        # Create new session
        host_and_port = '{}:{}'.format(hostname, host.data.winrm_port)
        logger.debug('host_and_port: %s', host_and_port)

        session = winrm.Session(
            host_and_port,
            auth=(
                kwargs['username'],
                kwargs['password'],
            ),
            transport=kwargs['winrm_transport'],
            read_timeout_sec=kwargs['winrm_read_timeout_sec'],
            operation_timeout_sec=kwargs['winrm_operation_timeout_sec'],
        )

        return session

    # TODO: add exceptions here
    except Exception as e:
        auth_kwargs = {}

        for key, value in kwargs.items():
            if key in ('username', 'password'):
                auth_kwargs[key] = value

        auth_args = ', '.join(
            '{0}={1}'.format(key, value)
            for key, value in auth_kwargs.items()
        )
        logger.debug('%s', e)
        _raise_connect_error(host, 'Authentication error', auth_args)


def run_shell_command(
    state, host, command,
    env=None,
    success_exit_codes=None,
    print_output=False,
    print_input=False,
    return_combined_output=False,
    shell_executable=Config.SHELL,
    **ignored_command_kwargs
):
    '''
    Execute a command on the specified host.

    Args:
        state (``pyinfra.api.State`` obj): state object for this command
        hostname (string): hostname of the target
        command (string): actual command to execute
        success_exit_codes (list): all values in the list that will return success
        print_output (boolean): print the output
        print_intput (boolean): print the input
        return_combined_output (boolean): combine the stdout and stderr lists
        shell_executable (string): shell to use - 'sh'=cmd, 'ps'=powershell(default)
        env (dict): environment variables to set

    Returns:
        tuple: (exit_code, stdout, stderr)
        stdout and stderr are both lists of strings from each buffer.
    '''

    command = make_win_command(command, env=env)

    logger.debug('Running command on %s: %s', host.name, command)

    if print_input:
        click.echo('{0}>>> {1}'.format(host.print_prefix, command), err=True)

    # get rid of leading/trailing quote
    tmp_command = command.strip("'")

    if print_output:
        click.echo(
            '{0}>>> {1}'.format(host.print_prefix, command),
            err=True,
        )

    if not shell_executable:
        shell_executable = 'ps'
    logger.debug('shell_executable:%s', shell_executable)

    # default windows to use ps, but allow it to be overridden
    if shell_executable in ['cmd']:
        response = host.connection.run_cmd(tmp_command)
    else:
        response = host.connection.run_ps(tmp_command)

    return_code = response.status_code
    logger.debug('response:%s', response)

    std_out_str = response.std_out.decode('utf-8')
    std_err_str = response.std_err.decode('utf-8')

    # split on '\r\n' (windows newlines)
    std_out = std_out_str.split('\r\n')
    std_err = std_err_str.split('\r\n')

    logger.debug('std_out:%s', std_out)
    logger.debug('std_err:%s', std_err)

    if print_output:
        click.echo(
            '{0}>>> {1}'.format(host.print_prefix, '\n'.join(std_out)),
            err=True,
        )

    if success_exit_codes:
        status = return_code in success_exit_codes
    else:
        status = return_code == 0

    logger.debug('Command exit status: %s', status)

    if return_combined_output:
        std_out = [('stdout', line) for line in std_out]
        std_err = [('stderr', line) for line in std_err]
        return status, std_out + std_err

    return status, std_out, std_err


def get_file(
    state, host, remote_filename, filename_or_io,
    **command_kwargs
):
    raise PyinfraError('Not implemented')


def put_file(
    state, host, filename_or_io, remote_filename,
    **command_kwargs
):
    raise PyinfraError('Not implemented')


EXECUTION_CONNECTOR = True
