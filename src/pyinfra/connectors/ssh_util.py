from getpass import getpass
from os import path
from typing import TYPE_CHECKING, Type, Union

from paramiko import (
    DSSKey,
    ECDSAKey,
    Ed25519Key,
    PasswordRequiredException,
    PKey,
    RSAKey,
    SSHException,
)

import pyinfra
from pyinfra.api.exceptions import ConnectError, PyinfraError

if TYPE_CHECKING:
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


def raise_connect_error(host: "Host", message, data):
    message = "{0} ({1})".format(message, data)
    raise ConnectError(message)


def _load_private_key_file(filename: str, key_filename: str, key_password: str):
    exception: Union[PyinfraError, SSHException] = PyinfraError("Invalid key: {0}".format(filename))

    key_cls: Union[Type[RSAKey], Type[DSSKey], Type[ECDSAKey], Type[Ed25519Key]]

    for key_cls in (RSAKey, DSSKey, ECDSAKey, Ed25519Key):
        try:
            return key_cls.from_private_key_file(
                filename=filename,
            )

        except PasswordRequiredException:
            if not key_password:
                # If password is not provided, but we're in CLI mode, ask for it. I'm not a
                # huge fan of having CLI specific code in here, but it doesn't really fit
                # anywhere else without duplicating lots of key related code into cli.py.
                if pyinfra.is_cli:
                    key_password = getpass(
                        "Enter password for private key: {0}: ".format(
                            key_filename,
                        ),
                    )

                # API mode and no password? We can't continue!
                else:
                    raise PyinfraError(
                        "Private key file ({0}) is encrypted, set ssh_key_password to "
                        "use this key".format(key_filename),
                    )

            try:
                return key_cls.from_private_key_file(
                    filename=filename,
                    password=key_password,
                )
            except SSHException as e:  # key does not match key_cls type
                exception = e
        except SSHException as e:  # key does not match key_cls type
            exception = e
    raise exception


def get_private_key(state: "State", key_filename: str, key_password: str) -> PKey:
    if key_filename in state.private_keys:
        return state.private_keys[key_filename]

    ssh_key_filenames = [
        # Global from executed directory
        path.expanduser(key_filename),
    ]

    if state.cwd:
        # Relative to the CWD
        path.join(state.cwd, key_filename)

    key = None
    key_file_exists = False

    for filename in ssh_key_filenames:
        if not path.isfile(filename):
            continue

        key_file_exists = True

        try:
            key = _load_private_key_file(filename, key_filename, key_password)
            break
        except SSHException:
            pass

    # No break, so no key found
    if not key:
        if not key_file_exists:
            raise PyinfraError("No such private key file: {0}".format(key_filename))
        raise PyinfraError("Invalid private key file: {0}".format(key_filename))

    # Load any certificate, names from OpenSSH:
    # https://github.com/openssh/openssh-portable/blob/049297de975b92adcc2db77e3fb7046c0e3c695d/ssh-keygen.c#L2453  # noqa: E501
    for certificate_filename in (
        "{0}-cert.pub".format(key_filename),
        "{0}.pub".format(key_filename),
    ):
        if path.isfile(certificate_filename):
            key.load_certificate(certificate_filename)

    state.private_keys[key_filename] = key
    return key
