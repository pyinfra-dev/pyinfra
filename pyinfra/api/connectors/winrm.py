from __future__ import print_function, unicode_literals

import click
import winrm

from pyinfra import logger
from pyinfra.api.exceptions import ConnectError
from pyinfra.api.util import make_win_command, memoize


def _raise_connect_error(host, message, data):
    message = '{0} ({1})'.format(message, data)
    raise ConnectError(message)


@memoize
# TODO: where should show_warning() be added?
def show_warning():
    logger.warning('The @winrm connector is pre-alpha!')


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

    # TODO: add more auth
    # pywinrm supports: basic, certificate, ntlm, kerberos, plaintext, ssl, credssp
    # see https://github.com/diyan/pywinrm/blob/master/winrm/__init__.py#L12

    return kwargs


def connect(state, host):
    '''
    Connect to a single host. Returns the winrm Session if successful.
    '''

    kwargs = _make_winrm_kwargs(state, host)
    logger.debug('Connecting to: {0} ({1})'.format(host.name, kwargs))

    # TODO: create a ~/.winrm/config file?
    # Hostname can be provided via winrm config (alias), data, or the hosts name
    hostname = kwargs.pop(
        'hostname',
        host.data.winrm_hostname or host.name,
    )

    logger.debug('winrm_username:{}'.format(host.data.winrm_username))
    logger.debug('winrm_password:{}'.format(host.data.winrm_password))
    logger.debug('winrm_port:{}'.format(host.data.winrm_port))
    logger.debug('use_shell:{}'.format(host.data.use_shell))

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
    return_combined_output=False,
    **command_kwargs
):
    '''
    Execute a command on the specified host.

    Args:
        state (``pyinfra.api.State`` obj): state object for this command
        hostname (string): hostname of the target
        command (string): actual command to execute
        sudo (boolean): Not used for WINRM
        sudo_user (string): Not used for WINRM
        use_sudo_login(boolean): Not used for WINRM
        use_su_login(boolean): Not used for WINRM
        preserve_sudo_env(boolean): Not used for WINRM
        get_pty (boolean): Not used for WINRM
        env (dict): envrionment variables to set
        timeout (int): timeout for this command to complete before erroring

    Returns:
        tuple: (exit_code, stdout, stderr)
        stdout and stderr are both lists of strings from each buffer.
    '''

    command = make_win_command(command, **command_kwargs)

    logger.debug('Running command on {0}: {1}'.format(host.name, command))

    # get rid of leading/trailing quote
    tmp_command = command.strip("'")

    if print_output:
        click.echo('{0}>>> {1}'.format(host.print_prefix, command))

    if state.config.SHELL == 'cmd':
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
        click.echo('{0}>>> {1}'.format(host.print_prefix, '\n'.join(std_out)))

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
    # TODO: implement
    return True


def put_file(
    state, host, filename_or_io, remote_filename,
    **command_kwargs
):
    # TODO: implement
    return True
