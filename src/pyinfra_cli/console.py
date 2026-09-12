"""
Shared Rich consoles and output adapters for the CLI (keeping the legacy
``click.style``/``click.echo`` call signatures used across the core library).

pyinfra keeps all human-facing output on **stderr** and reserves **stdout** for
machine-readable (``--json``) payloads.  The core library styles/echoes text
through :mod:`pyinfra.api.output`; here we install Rich-backed implementations.
"""

from __future__ import annotations

from functools import cache
from typing import Any

from rich.console import Console, RenderableType
from rich.padding import Padding
from rich.syntax import Syntax
from rich.text import Text

from pyinfra.api.output import get_console

from . import routing

# Human-facing console (logs, tables, prompts, spinner) → stderr.
# Reuse the core shared console so the progress spinner and logging write to the
# same Console instance (avoids Live-region corruption).
console = get_console()

# Machine-readable console (``--json`` payloads) → stdout, no styling.
stdout_console = Console(highlight=False, soft_wrap=True, markup=False, emoji=False)

# Detached console used ONLY to render styled text to ANSI in format_text().
# It must not be the shared console: capturing on a console with an active
# Live region would embed the whole re-rendered live frame in the capture.
_capture_console = Console(
    stderr=True,
    highlight=False,
    soft_wrap=True,
    markup=False,
    emoji=False,
)


def diff_renderable(diff_text: str, indent: int = 0) -> RenderableType:
    """Render a plain unified diff as a syntax-highlighted block.

    ``ansi_dark`` uses the terminal's ANSI palette (theme-friendly) and
    ``background_color="default"`` avoids a solid block against the terminal
    background — important inside the live region.
    """
    syntax = Syntax(
        diff_text,
        "diff",
        background_color="default",
        theme="ansi_dark",
        word_wrap=True,
    )
    if indent:
        return Padding(syntax, (0, 0, 0, indent))
    return syntax


@cache
def _style_codes(style: str) -> tuple[str, str]:
    """ANSI (prefix, suffix) escape codes for a Rich style string, cached.

    ``format_text`` runs in hot paths (per command-output/log/diff line), so
    the style→ANSI rendering is done once per style instead of per call.
    """
    with _capture_console.capture() as capture:
        _capture_console.print(Text("|", style=style), end="")
    prefix, _, suffix = capture.get().partition("|")
    return prefix, suffix


def format_text(text: str, fg: str | None = None, *, bold: bool = False, **kwargs: Any) -> str:
    """
    Style ``text`` and return a string with embedded ANSI codes.

    Mirrors the legacy ``click.style`` signature (positional foreground color +
    ``bold=``) used across the core library, but renders via Rich so styling is
    consistent with the rest of the CLI output.  Colour names (``red``,
    ``green``, ...) are passed straight through to Rich; other styling kwargs
    are ignored.
    """
    style_bits = []
    if fg is not None:
        style_bits.append(fg)
    if bold:
        style_bits.append("bold")

    if not style_bits:
        return text

    prefix, suffix = _style_codes(" ".join(style_bits))
    return f"{prefix}{text}{suffix}"


def echo(message: Any = None, *, err: bool = False, nl: bool = True, **kwargs: Any) -> None:
    """
    Print ``message`` to the appropriate console.

    ``err=True`` targets the (default) human stderr console; ``err=False``
    targets stdout.  ``nl=False`` suppresses the trailing newline.  Text may
    contain ANSI escape codes already produced by :func:`format_text`.

    When the live progress tree is active, host-attributed messages (command
    input/output, transfer notices, ...) are routed into the host's tree node
    instead of streaming to the console.
    """
    if err and isinstance(message, str):
        tree = routing.get_tree()
        if tree is not None and tree.is_active:
            host_name, text = routing.attribute_host(message)
            if host_name is not None:
                tree.add_host_detail(host_name, text)
                return

    target = console if err else stdout_console
    end = "\n" if nl else ""

    if message is None:
        target.print("", end=end)
        return

    if isinstance(message, str):
        target.print(Text.from_ansi(message), end=end)
    else:
        target.print(message, end=end)
