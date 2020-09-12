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
        ('timeout', state.config.CONNECT_TIMEOUT),
    ):
        if value:
            kwargs[key] = value

    # Password auth (boo!)
    if host.data.winrm_password:
        kwargs['password'] = host.data.winrm_password

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
    logger.debug('Connecting to: {0} ({1})'.format(host.name, kwargs))

    # Hostname can be provided via winrm config (alias), data, or the hosts name
    hostname = kwargs.pop(
        'hostname',
        host.data.winrm_hostname or host.name,
    )

    logger.debug('winrm_username:{} winrm_password:{} '
                 'winrm_port:{}'.format(host.data.winrm_username, host.data.winrm_password,
                                        host.data.winrm_port))

    try:
        # Create new session
        host_and_port = '{}:{}'.format(hostname, host.data.winrm_port)
        logger.debug('host_and_port: {}'.format(host_and_port))

        session = winrm.Session(
            host_and_port,
            auth=(
                host.data.winrm_username,
                host.data.winrm_password,
            ),
        )

        return session

    # TODO: add exceptions here
    except Exception as e:
        auth_kwargs = {}

        for key, value in kwargs.items():
            if key in ('username', 'password'):
                auth_kwargs[key] = value
                continue

        auth_args = ', '.join(
            '{0}={1}'.format(key, value)
            for key, value in auth_kwargs.items()
        )
        logger.debug(str(e))
        _raise_connect_error(host, 'Authentication error', auth_args)


def run_shell_command(
    state, host, command,
    get_pty=False,
    sudo=None,
    sudo_user=None,
    su_user=None,
    use_sudo_login=False,
    use_su_login=False,
    preserve_sudo_env=False,
    timeout=None,
    stdin=None,
    success_exit_codes=None,
    print_output=False,
    print_input=False,
    return_combined_output=False,
    shell_executable=Config.SHELL,
    **command_kwargs
):
    '''
    Execute a command on the specified host.

    Args:
        state (``pyinfra.api.State`` obj): state object for this command
        hostname (string): hostname of the target
        command (string): actual command to execute
        get_pty (boolean): Not used for WINRM
        sudo (boolean): Not used for WINRM
        sudo_user (string): Not used for WINRM
        use_sudo_login(boolean): Not used for WINRM
        use_su_login(boolean): Not used for WINRM
        preserve_sudo_env(boolean): Not used for WINRM
    TODO: check if winrm has a timeout and use timeout param
        timeout (int): timeout for this command to complete before erroring
        stdin (string): Not used for WINRM
        success_exit_codes (list): all values in the list that will return success
        print_output (boolean): print the output
        TODO print_intput (boolean): print the input
        return_combined_output (boolean): combine the stdout and stderr lists
        shell_executable (string): shell to use - 'sh'=cmd, 'ps'=powershell(default)
        env (dict): environment variables to set

    Returns:
        tuple: (exit_code, stdout, stderr)
        stdout and stderr are both lists of strings from each buffer.
    '''

    command = make_win_command(command, **command_kwargs)

    logger.debug('Running command on {0}: {1}'.format(host.name, command))

    # get rid of leading/trailing quote
    tmp_command = command.strip("'")

    if print_output:
        click.echo(
            '{0}>>> {1}'.format(host.print_prefix, command),
            err=True,
        )

    if not shell_executable:
        shell_executable = 'ps'
    logger.debug('shell_executable:{0}'.format(shell_executable))

    # default windows to use ps, but allow it to be overridden
    if shell_executable in ['cmd']:
        response = host.connection.run_cmd(tmp_command)
    else:
        response = host.connection.run_ps(tmp_command)

    return_code = response.status_code
    logger.debug('response:{}'.format(response))

    std_out_str = response.std_out.decode('utf-8')
    std_err_str = response.std_err.decode('utf-8')

    # split on '\r\n' (windows newlines)
    std_out = std_out_str.split('\r\n')
    std_err = std_err_str.split('\r\n')

    logger.debug('std_out:{}'.format(std_out))
    logger.debug('std_err:{}'.format(std_err))

    if print_output:
        click.echo(
            '{0}>>> {1}'.format(host.print_prefix, '\n'.join(std_out)),
            err=True,
        )

    if success_exit_codes:
        status = return_code in success_exit_codes
    else:
        status = return_code == 0

    logger.debug('Command exit status: {0}'.format(status))

    if return_combined_output:
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
