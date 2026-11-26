"""
Pyinfra vault file encryption & decryption operations.

CLI:

    PYINFRA_VAULT_PASSWORD=foo pyinfra @local vault.encrypt plain.txt cipher.txt overwrite=true
    PYINFRA_VAULT_PASSWORD=foo pyinfra @local vault.decrypt cipher.txt plain2.txt overwrite=true
"""

from pyinfra import host, logger
from pyinfra.api import OperationError, operation
from pyinfra.api.command import FunctionCommand
from pyinfra.api.vault import decrypt_str, encrypt_str, get_password
from pyinfra.facts.files import File, FileContents

MARKER = b"$PYINFRA_VAULT"
HEADER = MARKER + b";1.0;AES256_GCM"
ITERATIONS = 600_000
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32


@operation()
def encrypt(plain_path: str, vault_path: str, overwrite=False):
    """
    Encrypt plain file into vault file.

    + plain_path: path of plain file to encrypt
    + vault_path: path of vault file to write
    + overwrite: whether to overwrite an existing vault file
    """

    password = get_password()
    if not password:
        raise OperationError("empty password")

    plain_lines = host.get_fact(FileContents, path=plain_path)
    if plain_lines is None:
        raise OperationError(f"plain file {plain_path} does not exist")

    if plain_lines and plain_lines[0].startswith(MARKER.decode()):
        host.log("Plain file looks like a vault", logger.warning)

    if host.get_fact(File, vault_path) is not None and not overwrite:
        raise OperationError(f"vault file {vault_path} already exists and `overwrite` is unset")

    yield FunctionCommand(encrypt_file, (plain_lines, vault_path, password), {})


@operation()
def decrypt(vault_path: str, plain_path: str, overwrite=False):
    """
    Decrypt vault file into plain file.

    + vault_path: path of vault file to decrypt
    + plain_path: path of plain file to write
    + overwrite: whether to overwrite an existing plain file
    """

    password = get_password()
    if not password:
        raise OperationError("empty password")

    vault_lines = host.get_fact(FileContents, path=vault_path)
    if vault_lines is None:
        raise OperationError(f"vault file {vault_path} does not exist")

    if vault_lines and not vault_lines[0].startswith(MARKER.decode()):
        host.log("Vault file does not look like a vault", logger.warning)

    if host.get_fact(File, plain_path) is not None and not overwrite:
        raise OperationError(f"plain file {plain_path} already exists and `overwrite` is unset")

    yield FunctionCommand(decrypt_file, (vault_lines, plain_path, password), {})


def encrypt_file(plain_lines: str, vault_path: str, password: str):
    """
    Encrypt plain lines and write to vault file.
    """
    plain = "\n".join(plain_lines)
    with open(vault_path, "w") as f:
        f.write(encrypt_str(plain, password))


def decrypt_file(vault_lines: str, plain_path: str, password):
    """
    Decrypt vault lines and write to plain file.
    """
    vault = "\n".join(vault_lines)
    with open(plain_path, "w") as f:
        f.write(decrypt_str(vault, password))
