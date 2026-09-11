from __future__ import annotations

from getpass import getpass
from pathlib import Path
from typing import TYPE_CHECKING

from asyncssh import (
    KeyEncryptionError,
    KeyImportError,
    SSHCertificate,
    SSHKey,
    read_certificate,
    read_private_key,
)

import pyinfra
from pyinfra.api.exceptions import ConnectError, PyinfraError

if TYPE_CHECKING:
    from pyinfra.api.host import Host
    from pyinfra.api.state import State

KeyWithCertificate = tuple[SSHKey, SSHCertificate | None]


def raise_connect_error(host: Host, message, data):
    message = f"{message} ({data})"
    raise ConnectError(message)


def _needs_passphrase(e: KeyImportError) -> bool:
    return "passphrase" in str(e).lower()


def _load_private_key_file(
    filename: str,
    key_filename: str,
    key_password: str,
    allow_prompt: bool = True,
) -> SSHKey:
    try:
        return read_private_key(filename, passphrase=key_password or None)
    except KeyEncryptionError as e:
        raise PyinfraError(f"Incorrect password for private key: {key_filename}") from e
    except KeyImportError as e:
        if not _needs_passphrase(e):
            raise PyinfraError(f"Invalid private key file: {key_filename}") from e

        # If password is not provided, but we're in CLI mode, ask for it. I'm not a
        # huge fan of having CLI specific code in here, but it doesn't really fit
        # anywhere else without duplicating lots of key related code into cli.py.
        if pyinfra.is_cli and allow_prompt:
            key_password = getpass(f"Enter password for private key: {key_filename}: ")

        # No password and no prompt (API mode, or a non-interactive caller)? We can't continue.
        else:
            raise PyinfraError(
                f"Private key file ({key_filename}) is encrypted, set ssh_key_password to "
                "use this key",
            )

    try:
        return read_private_key(filename, passphrase=key_password)
    except (KeyImportError, KeyEncryptionError) as e:
        raise PyinfraError(f"Incorrect password for private key: {key_filename}") from e


def _resolve_key_paths(key_filename: str, cwd: str | None = None) -> list[str]:
    candidates = [str(Path(key_filename).expanduser())]
    if cwd:
        candidates.append(str(Path(cwd) / Path(key_filename).expanduser()))
    return candidates


def load_key_with_certificate(
    key_filename: str,
    key_password: str | None = None,
    certificate_filename: str | None = None,
    cwd: str | None = None,
    allow_prompt: bool = True,
) -> KeyWithCertificate:
    """
    Load a private key from disk along with an OpenSSH certificate when one is
    available, returning ``(key, certificate_or_None)`` ready to pass to asyncssh.

    + key_filename: path to the private key (``~`` is expanded).
    + key_password: passphrase if the key is encrypted, otherwise empty.
    + certificate_filename: explicit certificate path (eg. from an ssh_config
      ``CertificateFile`` directive). When unset, the adjacent
      ``<key>-cert.pub`` is used if present.
    + cwd: optional working directory used to resolve relative key paths.
    + allow_prompt: when False, an encrypted key with no known passphrase raises
      instead of prompting. Prompting is already limited to CLI runs, so API mode
      always raises.
    """

    resolved_path: str | None = None
    key: SSHKey | None = None
    key_file_exists = False

    for candidate in _resolve_key_paths(key_filename, cwd):
        if not Path(candidate).is_file():
            continue
        key_file_exists = True
        key = _load_private_key_file(
            candidate,
            key_filename,
            key_password or "",
            allow_prompt=allow_prompt,
        )
        resolved_path = candidate
        break

    if key is None or resolved_path is None:
        if not key_file_exists:
            raise PyinfraError(f"No such private key file: {key_filename}")
        raise PyinfraError(f"Invalid private key file: {key_filename}")

    # OpenSSH certificate name (eg. ``id_ed25519-cert.pub``):
    # https://github.com/openssh/openssh-portable/blob/049297de975b92adcc2db77e3fb7046c0e3c695d/ssh-keygen.c#L2453  # noqa: E501
    # Anchor the implicit search on the path the key actually loaded from so
    # ``~/...`` and other relative inputs resolve consistently.
    certificate: SSHCertificate | None = None
    if certificate_filename is not None:
        expanded_cert = str(Path(certificate_filename).expanduser())
        if Path(expanded_cert).is_file():
            certificate = read_certificate(expanded_cert)
    else:
        implicit_cert = f"{resolved_path}-cert.pub"
        if Path(implicit_cert).is_file():
            certificate = read_certificate(implicit_cert)

    return key, certificate


def get_private_key(state: State, key_filename: str, key_password: str) -> KeyWithCertificate:
    if key_filename in state.private_keys:
        return state.private_keys[key_filename]

    key = load_key_with_certificate(
        key_filename=key_filename,
        key_password=key_password,
        cwd=state.cwd,
    )

    state.private_keys[key_filename] = key
    return key
