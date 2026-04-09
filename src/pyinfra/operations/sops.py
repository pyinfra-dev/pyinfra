"""
Manage secrets in `SOPS <https://github.com/getsops/sops>`_-encrypted files.

SOPS (Secrets OPerationS) is an open-source tool for encrypting files using
age, GPG, AWS KMS, GCP KMS, or Azure Key Vault.

.. tip::
    The ``sops`` binary must be present on the target host. Use
    :attr:`config.INHERIT_ENV <pyinfra.api.Config.INHERIT_ENV>` to forward the
    age key from the machine running pyinfra:

    .. code:: python

        from pyinfra import config
        config.INHERIT_ENV = ["SOPS_AGE_KEY"]
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import OperationError, operation

from pyinfra.facts.sops import SopsKey


@operation()
def key(
    secrets_file: str,
    key: str,
    value: str | None = None,
    present: bool = True,
):
    """
    Ensure a key exists (or is absent) in a SOPS-encrypted file.

    + secrets_file: path to the SOPS-encrypted file (JSON or YAML)
    + key: top-level key name to set or remove
    + value: value to set — required when ``present=True``
    + present: whether the key should be present (default: ``True``)

    **Bootstrap** — set a key only if it does not already exist:

    .. code:: python

        import secrets
        from pyinfra import host
        from pyinfra.facts.sops import SopsKey

        if host.get_fact(SopsKey, secrets_file="secrets.enc.json", key="db_password") is None:
            sops.key(
                name="Bootstrap DB password",
                secrets_file="secrets.enc.json",
                key="db_password",
                value=secrets.token_urlsafe(32),
            )

    **Removing a key** (sets it to JSON ``null``):

    .. code:: python

        sops.key(
            name="Remove runner token",
            secrets_file="/path/to/secrets.enc.json",
            key="gitlab_runner_token",
            present=False,
        )

    .. note::
        Removal sets the key to ``null`` rather than deleting it, because SOPS
        does not currently support key deletion. Use ``null`` as a sentinel for
        absent values.
    """
    if present and value is None:
        raise OperationError("`value` is required when `present=True`")

    current = host.get_fact(SopsKey, secrets_file=secrets_file, key=key)

    if present:
        assert isinstance(value, str)  # for mypy narrowing
        if current == value:
            host.noop(f"Key '{key}' already set to the expected value in {secrets_file}")
            return
        escaped = value.replace('"', '\\"')
        yield f'sops --set \'["{key}"] "{escaped}"\' "{secrets_file}"'
    else:
        if current is None:
            host.noop(f"Key '{key}' already absent (null) in {secrets_file}")
            return
        yield f'sops --set \'["{key}"] null\' "{secrets_file}"'
