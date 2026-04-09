"""
Facts to read values from `SOPS <https://github.com/getsops/sops>`_-encrypted files.
"""

from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase


class SopsKey(FactBase[str | None]):
    """
    Returns the decrypted string value of a key from a SOPS-encrypted file,
    or ``None`` if the key does not exist or the decryption fails.

    Supports any file format recognised by ``sops`` (JSON, YAML, INI, ENV).
    The format is auto-detected from the file extension.

    Requires ``sops`` to be installed and a valid key available, either via
    ``~/.config/sops/age/keys.txt`` or the ``SOPS_AGE_KEY`` environment variable.

    Designed for use on ``@local`` — ``sops`` and the decryption key are not
    expected to be present on remote hosts.

    .. code:: python

        host.get_fact(SopsKey, secrets_file="/path/to/secrets.enc.json", key="my_token")
        # "glrt-xxxx..."

        host.get_fact(SopsKey, secrets_file="/path/to/secrets.enc.json", key="missing")
        # None
    """

    @override
    @staticmethod
    def default() -> str | None:
        return None

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "sops"

    @override
    def command(self, secrets_file: str, key: str) -> str:
        return f'sops --decrypt --extract \'["{key}"]\' "{secrets_file}" 2>/dev/null || true'

    @override
    def process(self, output: list[str]) -> str | None:
        value = "".join(output).strip()
        return value if value else None
