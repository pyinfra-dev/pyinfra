"""
Pyinfra vault file encryption & decryption.

Usage:

    from pyinfra.api import vault

    config.SUDO_PASSWORD = vault.decrypt('vault.txt', password='...', json=True)['root_pass']

Vault password comes from the PYINFRA_VAULT_PASSWORD environment variable.
If unset or empty, it's read via interactive prompt.
"""

import binascii
import getpass
import os
import secrets
from json import loads

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MARKER = b"$PYINFRA_VAULT"
HEADER = MARKER + b";1.0;AES256_GCM"
ITERATIONS = 600_000
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32


def load(vault_path: str, password: str = "", json: bool = False):
    if not password:
        password = get_password()

    with open(vault_path) as f:
        plaintext = decrypt_str(f.read(), password)

    if json:
        return loads(plaintext)

    return plaintext


def encrypt_str(plain: str, password: str) -> str:
    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)

    key = _derive_key(password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, plain.encode(), HEADER)

    return b"\n".join(
        [
            HEADER,
            binascii.hexlify(salt),
            binascii.hexlify(nonce),
            binascii.hexlify(ciphertext, sep="\n", bytes_per_sep=-32),
        ]
    ).decode("utf-8")


def decrypt_str(vault: str, password: str) -> str:
    lines = vault.strip().splitlines()
    if len(lines) < 4 or lines[0] != HEADER.decode("utf-8"):
        raise ValueError("Invalid or unsupported vault")

    salt = binascii.unhexlify(lines[1])
    nonce = binascii.unhexlify(lines[2])
    cipher = binascii.unhexlify("".join(lines[3:]))

    if len(salt) != SALT_SIZE or len(nonce) != NONCE_SIZE:
        raise ValueError("Invalid salt or nonce")

    key = _derive_key(password, salt)
    plaintext = AESGCM(key).decrypt(nonce, cipher, HEADER)

    return plaintext.decode("utf-8")


def get_password() -> str:
    password = os.getenv("PYINFRA_VAULT_PASSWORD")
    if not password:
        password = getpass.getpass("Vault password: ")

    return password


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=KEY_SIZE, salt=salt, iterations=ITERATIONS)
    return kdf.derive(password.encode("utf-8"))
