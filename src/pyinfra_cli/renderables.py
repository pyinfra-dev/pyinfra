"""
Registry mapping rich-free output descriptors (:mod:`pyinfra.api.renderable`) to
Rich renderables.

Operations/facts emit plain :class:`~pyinfra.api.renderable.OutputBlock`
descriptors via ``host.log_rich``; the CLI resolves each to a Rich renderable
here. New descriptor types register a renderer with
:func:`register_renderable`, so the routing/rendering pipeline stays generic.
"""

from __future__ import annotations

from collections.abc import Callable

from rich.console import RenderableType
from rich.padding import Padding
from rich.syntax import Syntax
from rich.text import Text

from pyinfra.api.renderable import CodeBlock, Diff, OutputBlock

from .console import diff_renderable

_RENDERERS: dict[type[OutputBlock], Callable[[OutputBlock], RenderableType]] = {}


def register_renderable(
    cls: type[OutputBlock],
    fn: Callable[[OutputBlock], RenderableType],
) -> None:
    """Register the Rich renderer for a descriptor type."""
    _RENDERERS[cls] = fn


def _lookup(descriptor: OutputBlock) -> Callable[[OutputBlock], RenderableType] | None:
    # Walk the MRO so a subclass without its own renderer falls back to a
    # registered base renderer.
    for klass in type(descriptor).__mro__:
        fn = _RENDERERS.get(klass)  # type: ignore[arg-type]
        if fn is not None:
            return fn
    return None


def to_renderable(descriptor: OutputBlock, indent: int = 0) -> RenderableType:
    """Turn a descriptor into a Rich renderable, indented if requested.

    Unknown descriptor types degrade to their ``repr`` rather than crashing.
    """
    fn = _lookup(descriptor)
    renderable: RenderableType = fn(descriptor) if fn is not None else Text(repr(descriptor))
    if indent:
        return Padding(renderable, (0, 0, 0, indent))
    return renderable


# Built-in renderers (registered at import time).
register_renderable(Diff, lambda d: diff_renderable(d.text))  # type: ignore[attr-defined]
register_renderable(
    CodeBlock,
    lambda d: Syntax(
        d.text,  # type: ignore[attr-defined]
        d.lexer,  # type: ignore[attr-defined]
        background_color="default",
        theme="ansi_dark",
        word_wrap=True,
    ),
)
