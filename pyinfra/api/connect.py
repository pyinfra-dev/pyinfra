# pyinfra
# File: pyinfra/api/connect.py
# Desc: handle connecting to the inventory

from getpass import getpass
from os import path

import gevent
import six

from paramiko import (
    PasswordRequiredException,
    RSAKey,
    SSHException,
)

from pyinfra.api.exceptions import PyinfraError


def _get_private_key(state, key_filename, key_password):
    if key_filename in state.private_keys:
        return state.private_keys[key_filename]

    ssh_key_filenames = [
        # Global from executed directory
        path.expanduser(key_filename),
    ]

    # Relative to the deploy
    if state.deploy_dir:
        ssh_key_filenames.append(
            path.join(state.deploy_dir, key_filename),
        )

    for filename in ssh_key_filenames:
        if not path.isfile(filename):
            continue

        # First, lets try the key without a password
        try:
            key = RSAKey.from_private_key_file(
                filename=filename,
            )
            break

        # Key is encrypted!
        except PasswordRequiredException:
            # If password is not provided, but we're in CLI mode, ask for it. I'm not a
            # huge fan of having CLI specific code in here, but it doesn't really fit
            # anywhere else without duplicating lots of key related code into cli.py.
            if not key_password:
                if state.is_cli:
                    key_password = getpass(
                        'Enter password for private key: {0}: '.format(
                            key_filename,
                        ),
                    )

            # API mode and no password? We can't continue!
                else:
                    raise PyinfraError(
                        'Private key file ({0}) is encrypted, set ssh_key_password to '
                        'use this key'.format(key_filename),
                    )

            # Now, try opening the key with the password
            try:
                key = RSAKey.from_private_key_file(
                    filename=filename,
                    password=key_password,
                )
                break

            except SSHException:
                raise PyinfraError(
                    'Incorrect password for private key: {0}'.format(
                        key_filename,
                    ),
                )

    # No break, so no key found
    else:
        raise IOError('No such private key file: {0}'.format(key_filename))

    state.private_keys[key_filename] = key
    return key


def connect_all(state, progress=None):
    '''
    Connect to all the configured servers in parallel. Reads/writes state.inventory.

    Args:
        state (``pyinfra.api.State`` obj): the state containing an inventory to connect to
    '''

    greenlets = {}

    for host in state.inventory:
        kwargs = {
            'username': host.data.ssh_user,
            'port': int(host.data.ssh_port) if host.data.ssh_port else 22,
            'timeout': state.config.TIMEOUT,
            # At this point we're assuming a password/key are provided
            'allow_agent': False,
            'look_for_keys': False,
        }

        # Password auth (boo!)
        if host.data.ssh_password:
            kwargs['password'] = host.data.ssh_password

        # Key auth!
        elif host.data.ssh_key:
            kwargs['pkey'] = _get_private_key(
                state,
                key_filename=host.data.ssh_key,
                key_password=host.data.ssh_key_password,
            )

        # No key or password, so let's have paramiko look for SSH agents and user keys
        else:
            kwargs['allow_agent'] = True
            kwargs['look_for_keys'] = True

        greenlets[host.name] = state.pool.spawn(
            host.connect,
            state,
            **kwargs
        )

    # Wait for all the connections to complete
    for _ in gevent.iwait(greenlets.values()):
        # Trigger CLI progress if provided
        if progress:
            progress()

    # Get/set the results
    failed_hosts = set()
    connected_host_names = set()

    for name, greenlet in six.iteritems(greenlets):
        client = greenlet.get()

        if not client:
            failed_hosts.add(name)
        else:
            connected_host_names.add(name)

    # Add connected hosts to inventory
    state.connected_host_names = connected_host_names

    # Add all the hosts as active
    state.active_host_names = set(greenlets.keys())

    # Remove those that failed, triggering FAIL_PERCENT check
    state.fail_hosts(failed_hosts)
