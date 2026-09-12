"""
Host attribution & routing of log/echo messages.

When the live progress tree is active, per-host log and echo lines are routed
into the host's tree node instead of streaming to the console (which would
corrupt the live region).  Warnings/errors are also recorded per host so
failure prompts can display *which* hosts failed and why.

Attribution uses ``pyinfra.context.ctx_host`` when set in the calling greenlet
and falls back to parsing the rendered ``host.print_prefix`` at the start of
the message (command-output reader greenlets and connect-phase greenlets do
not inherit the host context, but their lines carry the prefix).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rich.text import Text

from pyinfra.context import ctx_host

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .progress import DeployProgress

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

# Matches a leading connector prefix, e.g. "@docker/" or "@fake/".
CONNECTOR_PREFIX_RE = re.compile(r"^(@[^/]+/)(.*)$")


def host_label(name: str, base_style: str = "", prefix: str = "") -> Text:
    """
    Render a host name as Rich ``Text`` with any ``@connector/`` prefix dimmed.

    ``prefix`` is prepended verbatim (e.g. tree indentation).
    """
    text = Text(prefix)
    match = CONNECTOR_PREFIX_RE.match(name)
    if match:
        connector, rest = match.groups()
        text.append(connector, style="dim")
        text.append(rest, style=base_style)
    else:
        text.append(name, style=base_style)
    return text


_tree: DeployProgress | None = None
_host_names: list[str] = []  # sorted longest-first for prefix matching
_host_names_set: set[str] = set()
_has_whitespace_names = False
_host_errors: dict[str, list[str]] = {}


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def set_tree(tree: DeployProgress | None) -> None:
    """Register (or clear) the active live tree renderer."""
    global _tree
    _tree = tree


def get_tree() -> DeployProgress | None:
    return _tree


def set_host_names(names: Iterable[str]) -> None:
    """Register the inventory host names used for prefix attribution."""
    global _host_names, _host_names_set, _has_whitespace_names
    _host_names = sorted(names, key=len, reverse=True)
    _host_names_set = set(_host_names)
    _has_whitespace_names = any(" " in name for name in _host_names)


def reset_host_errors() -> None:
    _host_errors.clear()


def record_host_error(host_name: str, message: str) -> None:
    _host_errors.setdefault(host_name, []).append(message)


def get_host_errors() -> dict[str, list[str]]:
    return _host_errors


def split_host_prefix(plain: str) -> tuple[str | None, str]:
    """
    Split a plain (ANSI-stripped) message into ``(host_name, rest)`` when it
    starts with a known host prefix, else ``(None, message)``.

    Supports both the legacy ``[hostname]`` bracketed form and the plain
    ``hostname`` form. The prefix is always ``name`` + padding + space, so the
    common case is an O(1) lookup of the first whitespace-delimited token; the
    linear prefix scan only remains for host names containing whitespace.
    """
    s = plain.lstrip()

    if s.startswith("["):
        end = s.find("]")
        if end > 0 and s[1:end] in _host_names_set:
            return s[1:end], s[end + 1 :].lstrip()

    token = s.split(maxsplit=1)[0] if s else ""
    if token in _host_names_set:
        return token, s[len(token) :].lstrip()

    if _has_whitespace_names:
        for name in _host_names:
            if s.startswith(name):
                return name, s[len(name) :].lstrip()

    return None, plain.strip()


def attribute_host(message: str) -> tuple[str | None, str]:
    """
    Attribute a rendered log/echo ``message`` to a host.

    Returns ``(host_name | None, plain_detail_text)`` — the detail text is
    ANSI-stripped with any host prefix removed.
    """
    plain = strip_ansi(message)

    name, rest = split_host_prefix(plain)
    if name is not None:
        return name, rest

    if ctx_host.isset():
        host = ctx_host.get()
        return host.name, plain.strip()

    return None, plain.strip()
