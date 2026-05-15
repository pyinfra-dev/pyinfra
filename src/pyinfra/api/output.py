"""
Pluggable output formatting for pyinfra.

Provides ``format_text`` and ``echo`` functions that default to plain-text
no-ops, allowing the API layer to work without any CLI dependency.  The CLI
layer replaces them at startup via ``set_formatter`` and ``set_echo``.
"""

from __future__ import annotations

from typing import Any
from collections.abc import Callable


# Default formatter: identity function (returns plain text, ignores styling kwargs).
def _default_format_text(text: str, *args: Any, **kwargs: Any) -> str:
    return text


# Default echo: no-op.
def _default_echo(message: Any = None, **kwargs: Any) -> None:
    pass


_format_text: Callable[..., str] = _default_format_text
_echo: Callable[..., None] = _default_echo


def format_text(text: str, *args: Any, **kwargs: Any) -> str:
    """Format text with optional styling (color, bold, etc.).

    Mirrors ``click.style`` signature.  Accepts positional ``fg`` argument
    for compatibility with ``click.style("text", "red")``.
    """
    return _format_text(text, *args, **kwargs)


def echo(message: Any = None, **kwargs: Any) -> None:
    """Echo a message.  Mirrors ``click.echo`` signature."""
    return _echo(message, **kwargs)


def set_formatter(func: Callable[..., str]) -> None:
    """Replace the default formatter (e.g. with ``click.style``)."""
    global _format_text
    _format_text = func


def set_echo(func: Callable[..., None]) -> None:
    """Replace the default echo function (e.g. with ``click.echo``)."""
    global _echo
    _echo = func


def is_output_active() -> bool:
    """Return True if a non-default echo function has been installed."""
    return _echo is not _default_echo
