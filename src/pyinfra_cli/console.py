"""
Shared Rich consoles and Click-compatible output adapters for the CLI.

pyinfra keeps all human-facing output on **stderr** and reserves **stdout** for
machine-readable (``--json``) payloads.  The core library styles/echoes text
through :mod:`pyinfra.api.output`; here we install Rich-backed implementations.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.text import Text

from pyinfra.api.output import get_console, set_console

# Human-facing console (logs, tables, prompts, spinner) → stderr.
# Reuse the core shared console so the progress spinner and logging write to the
# same Console instance (avoids Live-region corruption).
console = get_console()
set_console(console)

# Machine-readable console (``--json`` payloads) → stdout, no styling.
stdout_console = Console(highlight=False, soft_wrap=True, markup=False, emoji=False)


def format_text(text: str, fg: str | None = None, *, bold: bool = False, **kwargs: Any) -> str:
    """
    Style ``text`` and return a string with embedded ANSI codes.

    Mirrors the legacy ``click.style`` signature (positional foreground color +
    ``bold=``) used across the core library, but renders via Rich so styling is
    consistent with the rest of the CLI output.  Colour names (``red``,
    ``green``, ...) are passed straight through to Rich.
    """
    style_bits = []
    if fg is not None:
        style_bits.append(fg)
    if bold:
        style_bits.append("bold")

    if not style_bits:
        return text

    rich_text = Text(text, style=" ".join(style_bits))
    with console.capture() as capture:
        console.print(rich_text, end="")
    return capture.get()


def echo(message: Any = None, *, err: bool = False, nl: bool = True, **kwargs: Any) -> None:
    """
    Print ``message`` to the appropriate console.

    ``err=True`` targets the (default) human stderr console; ``err=False``
    targets stdout.  ``nl=False`` suppresses the trailing newline.  Text may
    contain ANSI escape codes already produced by :func:`format_text`.
    """
    target = console if err else stdout_console
    end = "\n" if nl else ""

    if message is None:
        target.print("", end=end)
        return

    if isinstance(message, str):
        target.print(Text.from_ansi(message), end=end)
    else:
        target.print(message, end=end)
