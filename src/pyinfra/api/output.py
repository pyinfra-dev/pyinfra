"""
Pluggable output formatting for pyinfra.

Provides ``format_text`` and ``echo`` functions that default to plain-text
no-ops, allowing the API layer to work without any CLI dependency.  The CLI
layer replaces them at startup via ``set_formatter`` and ``set_echo`` (wiring
in Rich-backed implementations).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from collections.abc import Callable

if TYPE_CHECKING:
    from rich.console import Console

_console: Console | None = None


def get_console() -> Console:
    """
    Return the shared human-facing (stderr) Rich console.

    Created lazily so importing the API layer doesn't require Rich to be
    configured.  The CLI may replace it via :func:`set_console` to share a
    single console between logging, tables and the progress spinner.
    """
    global _console
    if _console is None:
        from rich.console import Console

        # markup/emoji disabled: host print prefixes like ``[@fake/host]`` and
        # arbitrary command output must not be interpreted as Rich markup.
        _console = Console(
            stderr=True,
            highlight=False,
            soft_wrap=True,
            markup=False,
            emoji=False,
        )
    return _console


def set_console(console: Console) -> None:
    """Replace the shared human-facing console."""
    global _console
    _console = console


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

    Historically mirrored ``click.style``: accepts a positional foreground
    color (e.g. ``format_text("text", "red")``) and ``bold=`` keyword.  The CLI
    installs a Rich-backed implementation preserving this signature.
    """
    return _format_text(text, *args, **kwargs)


def echo(message: Any = None, **kwargs: Any) -> None:
    """Echo a message.  Supports ``err=True`` to write to stderr."""
    return _echo(message, **kwargs)


def set_formatter(func: Callable[..., str]) -> None:
    """Replace the default formatter (e.g. with a Rich-backed styler)."""
    global _format_text
    _format_text = func


def set_echo(func: Callable[..., None]) -> None:
    """Replace the default echo function (e.g. with a Rich-backed echo)."""
    global _echo
    _echo = func


def is_output_active() -> bool:
    """Return True if a non-default echo function has been installed."""
    return _echo is not _default_echo
