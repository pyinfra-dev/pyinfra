import re
import time

import click
import serial

from pyinfra import logger

from .util import (
    get_sudo_password,
    make_unix_command,
)

EXECUTION_CONNECTOR = True


def make_names_data(hostname):
    yield '@serial/' + hostname, {'serial_hostname': hostname}, []


def connect(state, host):
    speed = host.data.serial_speed or 9600
    logger.debug('Connecting to: %s', host.data.serial_hostname)
    return serial.Serial(host.data.serial_hostname, speed)


def run_shell_command(
    state, host, command,
    get_pty=False,
    timeout=None,
    stdin=None,
    success_exit_codes=None,
    print_output=False,
    print_input=False,
    return_combined_output=False,
    use_sudo_password=False,
    **command_kwargs
):

    if use_sudo_password:
        command_kwargs['use_sudo_password'] = get_sudo_password(
            state, host, use_sudo_password,
            run_shell_command=run_shell_command,
            put_file=put_file,
        )

    command = make_unix_command(command, **command_kwargs)
    logger.debug('Running command on %s: %s', host.name, command)
    actual_command = command.get_raw_value() + '\n'

    if print_input:
        click.echo('{0}>>> {1}'.format(host.print_prefix, command), err=True)

    num_bytes_written = host.connection.write(bytes(actual_command, encoding='ascii'))
    logger.debug('Num bytes written: %s', num_bytes_written)
    if host.data.serial_waittime is not None:
        time.sleep(host.data.serial_waittime)
    std_out = host.connection.read_all()

    host.connection.write(b'echo $?\n')
    host.connection.read_until(b'echo $?\r\r\n')
    time.sleep(1)
    status_and_rest = host.connection.read_all()
    try:
        status = int(re.match(rb'\d+', status_and_rest).group())
    except Exception:
        logger.debug('Could not fetch exit status, defaulting to 0')
        status = 0
    else:
        logger.debug('Status: %s', status)

    logger.debug('Command output: %s', std_out)
    if return_combined_output:
        return status, [('stdout', std_out)]
    return status, [std_out], ['']


def put_file(*a, **kw):
    raise NotImplementedError('File transfer per serial line is currently not supported')


def get_file(*a, **kw):
    raise NotImplementedError('File transfer per serial line is currently not supported')
