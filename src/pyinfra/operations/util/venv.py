from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pyinfra import logger


def _major_minor(version: Sequence[int]) -> str:
    return ".".join(str(part) for part in version[:2])


def check_existing_venv(
    description: str,
    current: Sequence[int] | None,
    wanted: Sequence[int] | None,
    python: str | None,
    on_mismatch: Literal["warn", "recreate", "ignore"],
) -> tuple[bool, str | None]:
    """
    Decide what to do with an existing Python virtual environment.

    + description: how messages name the environment, eg ``virtualenv /opt/venv``
    + current: version of the interpreter inside the environment, ``None`` if it cannot run
    + wanted: version of the interpreter the user asked for, ``None`` if it was not found
    + python: the interpreter the user asked for, ``None`` when they did not specify one
    + on_mismatch: ``warn`` or ``recreate``; ``ignore`` is for the caller to handle

    Returns ``(recreate, reason)``: whether the environment must be deleted and created again,
    and why it is not simply fine (``None`` when it is). An environment that is kept despite a
    reason has been logged as a warning.
    """

    if current is None:
        return True, "its Python interpreter cannot be executed"

    if python is None:
        return False, None

    if wanted is None:
        reason = f"the requested Python {python} was not found, so its version was not checked"
        logger.warning(f"{description} exists but {reason}")
        return False, reason

    if tuple(current[:2]) != tuple(wanted[:2]):
        reason = (
            f"runs Python {_major_minor(current)} while {python} is Python {_major_minor(wanted)}"
        )
        if on_mismatch == "recreate":
            return True, reason
        logger.warning(f'{description} {reason}; pass on_mismatch="recreate" to rebuild it')
        return False, reason

    return False, None
