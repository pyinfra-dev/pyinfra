from getpass import getpass
from os import path
from typing import TYPE_CHECKING

from paramiko import (
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
    message = f"{message} ({data})"
    raise ConnectError(message)


def _load_private_key_file(filename: str, key_filename: str, key_password: str):
    exception: PyinfraError | SSHException = PyinfraError(f"Invalid key: {filename}")

    key_cls: type[RSAKey] | type[ECDSAKey] | type[Ed25519Key]

    for key_cls in (RSAKey, ECDSAKey, Ed25519Key):
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
                        f"Enter password for private key: {key_filename}: ",
                    )

                # API mode and no password? We can't continue!
                else:
                    raise PyinfraError(
                        f"Private key file ({key_filename}) is encrypted, set ssh_key_password to "
                        "use this key",
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


def _resolve_key_paths(key_filename: str, cwd: str | None = None) -> list[str]:
    candidates = [path.expanduser(key_filename)]
    if cwd:
        candidates.append(path.join(cwd, path.expanduser(key_filename)))
    return candidates


def load_key_with_certificate(
    key_filename: str,
    key_password: str | None = None,
    certificate_filename: str | None = None,
    cwd: str | None = None,
) -> PKey:
    """
    Load a paramiko ``PKey`` from disk and attach an OpenSSH certificate when one
    is available. Has no dependency on pyinfra state so it can be reused both
    from the CLI key path (via :func:`get_private_key`) and from the ssh_config
    path in :mod:`pyinfra.connectors.sshuserclient`.

    + key_filename: path to the private key (``~`` is expanded).
    + key_password: passphrase if the key is encrypted, otherwise empty.
    + certificate_filename: explicit certificate path (eg. from an ssh_config
      ``CertificateFile`` directive). When unset, the adjacent
      ``<key>-cert.pub`` is used if present, falling back to ``<key>.pub``.
    + cwd: optional working directory used to resolve relative key paths.
    """

    resolved_path: str | None = None
    key: PKey | None = None
    key_file_exists = False

    for candidate in _resolve_key_paths(key_filename, cwd):
        if not path.isfile(candidate):
            continue
        key_file_exists = True
        try:
            key = _load_private_key_file(candidate, key_filename, key_password or "")
            resolved_path = candidate
            break
        except SSHException:
            pass

    if key is None or resolved_path is None:
        if not key_file_exists:
            raise PyinfraError(f"No such private key file: {key_filename}")
        raise PyinfraError(f"Invalid private key file: {key_filename}")

    # OpenSSH certificate name (eg. ``id_ed25519-cert.pub``):
    # https://github.com/openssh/openssh-portable/blob/049297de975b92adcc2db77e3fb7046c0e3c695d/ssh-keygen.c#L2453  # noqa: E501
    # Anchor the implicit search on the path the key actually loaded from so
    # ``~/...`` and other relative inputs resolve consistently. ``<key>.pub``
    # is intentionally skipped: it is the bare public key, not a certificate,
    # and ``load_certificate`` overwrites any previously-attached cert with a
    # non-cert public blob.
    if certificate_filename is not None:
        expanded_cert = path.expanduser(certificate_filename)
        if path.isfile(expanded_cert):
            key.load_certificate(expanded_cert)
    else:
        implicit_cert = f"{resolved_path}-cert.pub"
        if path.isfile(implicit_cert):
            key.load_certificate(implicit_cert)

    return key


def get_private_key(state: "State", key_filename: str, key_password: str) -> PKey:
    if key_filename in state.private_keys:
        return state.private_keys[key_filename]

    key = load_key_with_certificate(
        key_filename=key_filename,
        key_password=key_password,
        cwd=state.cwd,
    )

    state.private_keys[key_filename] = key
    return key
