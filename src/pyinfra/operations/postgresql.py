from __future__ import annotations

from pyinfra.api import operation

from . import postgres


@operation(is_idempotent=False, is_deprecated=True, deprecated_for="postgres.sql")
def sql(*args, **kwargs):
    yield from postgres.sql._inner(*args, **kwargs)


@operation(is_idempotent=False, is_deprecated=True, deprecated_for="postgres.role")
def role(*args, **kwargs):
    yield from postgres.role._inner(*args, **kwargs)


@operation(is_idempotent=False, is_deprecated=True)
def database(*args, **kwargs):
    yield from postgres.database._inner(*args, **kwargs)


@operation(is_idempotent=False, is_deprecated=True)
def dump(*args, **kwargs):
    yield from postgres.dump._inner(*args, **kwargs)


@operation(is_idempotent=False, is_deprecated=True)
def load(*args, **kwargs):
    yield from postgres.load._inner(*args, **kwargs)
