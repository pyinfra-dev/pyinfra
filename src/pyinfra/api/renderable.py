"""
Rich-free output descriptors for structured CLI output.

Operations and facts describe rich output (diffs, syntax-highlighted code
blocks, ...) with these plain dataclasses via :meth:`pyinfra.api.host.Host.log_rich`.
The core stays decoupled from any rendering library — the CLI layer
(``pyinfra_cli``) maps each descriptor to a Rich renderable via its registry.

New descriptor types only need a subclass here plus a CLI-side renderer
registration; the routing/rendering pipeline is generic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutputBlock:
    """Base marker for a structured, rich-free output descriptor."""


@dataclass(frozen=True)
class Diff(OutputBlock):
    """A unified-diff block (rendered with the ``diff`` lexer)."""

    text: str


@dataclass(frozen=True)
class CodeBlock(OutputBlock):
    """A syntax-highlighted code block.

    ``lexer`` is a Pygments lexer name (``sql``, ``yaml``, ``json``, ...).
    """

    text: str
    lexer: str = "text"
