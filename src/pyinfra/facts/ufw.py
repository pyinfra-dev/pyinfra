"""
Facts for `ufw <https://launchpad.net/ufw>`_ (Uncomplicated Firewall).

``UfwStatus`` exposes the host-wide state (active, logging, default policies)
parsed from ``ufw status verbose``. ``UfwRules`` parses the rules reported by
``ufw show added`` into canonical dicts so operations can perform a structured
diff against them.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional

from typing import Any

from typing_extensions import override

from pyinfra.api import FactBase

# Shape of a single rule returned by UfwRules / accepted by operations.
# Keys: action, direction, interface, from_, to, port, proto, app, log, comment.
UfwRuleDict = Dict[str, Optional[str]]

# Shape of UfwStatus: {"active": bool, "logging": str|None,
# "default": {"incoming": str, "outgoing": str, "routed": str},
# "new_profiles": str|None}
UfwStatusDict = Dict[str, Any]


_ACTIONS = ("allow", "deny", "reject", "limit")


def _canonical_rule(
    action: str,
    direction: Optional[str] = None,
    interface: Optional[str] = None,
    from_ip: Optional[str] = None,
    to_ip: Optional[str] = None,
    port: Optional[str] = None,
    proto: Optional[str] = None,
    app: Optional[str] = None,
    log: Optional[str] = None,
    comment: Optional[str] = None,
) -> UfwRuleDict:
    """Return a normalised ufw rule dict shared by the fact and operation."""

    if action not in _ACTIONS:
        raise ValueError("ufw action must be one of {0}, got {1!r}".format(_ACTIONS, action))
    if direction is not None and direction not in ("in", "out", "route"):
        raise ValueError("ufw direction must be in/out/route, got {0!r}".format(direction))
    if log is not None and log not in ("log", "log-all"):
        raise ValueError("ufw log must be log/log-all or None, got {0!r}".format(log))

    # app profiles are mutually exclusive with port/proto
    if app and (port or proto):
        raise ValueError("ufw rule cannot combine app profile with port/proto")

    port_str = str(port) if port is not None else None

    return {
        "action": action,
        "direction": direction,
        "interface": interface,
        "from_": from_ip,
        "to": to_ip,
        "port": port_str,
        "proto": proto,
        "app": app,
        "log": log,
        "comment": comment,
    }


_PORT_RE = re.compile(r"^(?P<port>[\w:,]+)(?:/(?P<proto>tcp|udp))?$")


def _parse_ufw_rule_line(line: str) -> Optional[UfwRuleDict]:
    """Parse a single ``ufw show added`` line into a canonical rule dict.

    Returns None if the line is a header or cannot be recognised.
    """

    line = line.strip()
    if not line or not line.startswith("ufw "):
        return None

    tokens = line.split()
    # tokens[0] == "ufw"
    idx = 1

    # Optional "route" keyword comes before the action.
    direction: Optional[str] = None
    if idx < len(tokens) and tokens[idx] == "route":
        direction = "route"
        idx += 1

    if idx >= len(tokens):
        return None

    action = tokens[idx]
    if action not in _ACTIONS:
        return None
    idx += 1

    log: Optional[str] = None
    if idx < len(tokens) and tokens[idx] in ("log", "log-all"):
        log = tokens[idx]
        idx += 1

    if idx < len(tokens) and tokens[idx] in ("in", "out"):
        # Override any earlier "route" (route has its own direction token).
        if direction is None:
            direction = tokens[idx]
        idx += 1

    interface: Optional[str] = None
    if idx + 1 < len(tokens) and tokens[idx] == "on":
        interface = tokens[idx + 1]
        idx += 2

    from_ip: Optional[str] = None
    to_ip: Optional[str] = None
    port: Optional[str] = None
    proto: Optional[str] = None
    app: Optional[str] = None
    comment: Optional[str] = None

    while idx < len(tokens):
        tok = tokens[idx]

        if tok == "from" and idx + 1 < len(tokens):
            from_ip = tokens[idx + 1]
            idx += 2
            continue
        if tok == "to" and idx + 1 < len(tokens):
            to_ip = tokens[idx + 1]
            idx += 2
            continue
        if tok == "port" and idx + 1 < len(tokens):
            port = tokens[idx + 1]
            idx += 2
            continue
        if tok == "proto" and idx + 1 < len(tokens):
            proto = tokens[idx + 1]
            idx += 2
            continue
        if tok == "app" and idx + 1 < len(tokens):
            app = tokens[idx + 1]
            idx += 2
            continue
        if tok == "comment":
            # Everything after "comment" and up to end of string; ufw quotes it.
            rest = " ".join(tokens[idx + 1 :])
            if rest.startswith("'") and rest.endswith("'"):
                rest = rest[1:-1]
            elif rest.startswith('"') and rest.endswith('"'):
                rest = rest[1:-1]
            comment = rest
            idx = len(tokens)
            continue

        # Short-form: "allow 22/tcp" or "allow 22" right after the action.
        # Only interpret if from/to have not been set yet.
        if port is None and from_ip is None and to_ip is None:
            match = _PORT_RE.match(tok)
            if match:
                port = match.group("port")
                proto = match.group("proto") or proto
                idx += 1
                continue

        # Unknown token: stop parsing, keep what we have.
        break

    return _canonical_rule(
        action=action,
        direction=direction,
        interface=interface,
        from_ip=from_ip,
        to_ip=to_ip,
        port=port,
        proto=proto,
        app=app,
        log=log,
        comment=comment,
    )


class UfwStatus(FactBase[UfwStatusDict]):
    """
    Returns the parsed output of ``ufw status verbose`` as a dict.

    .. code:: python

        {
            "active": True,
            "logging": "low",
            "default": {
                "incoming": "deny",
                "outgoing": "allow",
                "routed": "disabled",
            },
            "new_profiles": "skip",
        }

    When ufw is inactive the dict only contains ``{"active": False}``.
    """

    default = dict

    @override
    def requires_command(self) -> str:
        return "ufw"

    @override
    def command(self) -> str:
        return "ufw status verbose 2>/dev/null || true"

    @override
    def process(self, output: Iterable[str]) -> UfwStatusDict:
        result: Dict[str, Any] = {"active": False}

        for raw in output:
            line = raw.strip()
            if not line:
                continue

            if line.startswith("Status:"):
                result["active"] = line.split(":", 1)[1].strip().lower() == "active"
                continue

            if line.startswith("Logging:"):
                value = line.split(":", 1)[1].strip()
                # "on (low)" / "off"
                match = re.match(r"on\s*\(([^)]+)\)", value)
                if match:
                    result["logging"] = match.group(1)
                elif value.startswith("on"):
                    result["logging"] = "on"
                else:
                    result["logging"] = None
                continue

            if line.startswith("Default:"):
                default: Dict[str, str] = {}
                # "deny (incoming), allow (outgoing), disabled (routed)"
                body = line.split(":", 1)[1].strip()
                for chunk in body.split(","):
                    match = re.match(r"\s*(\S+)\s*\(([^)]+)\)", chunk)
                    if match:
                        default[match.group(2).strip()] = match.group(1).strip()
                result["default"] = default
                continue

            if line.startswith("New profiles:"):
                result["new_profiles"] = line.split(":", 1)[1].strip()
                continue

        return result


class UfwRules(FactBase[List[UfwRuleDict]]):
    """
    Returns the rules reported by ``ufw show added`` as a list of canonical
    dicts (see :func:`_canonical_rule`). Lines that are not user-added rules
    (headers, blank lines) are ignored.

    .. code:: python

        [
            {"action": "limit", "port": "22", "proto": "tcp", ...},
            {"action": "allow", "port": "51312", "proto": None, ...},
        ]
    """

    default = list

    @override
    def requires_command(self) -> str:
        return "ufw"

    @override
    def command(self) -> str:
        return "ufw show added 2>/dev/null || true"

    @override
    def process(self, output: Iterable[str]) -> List[UfwRuleDict]:
        rules: List[UfwRuleDict] = []
        for raw in output:
            parsed = _parse_ufw_rule_line(raw)
            if parsed is not None:
                rules.append(parsed)
        return rules


def _render_rule(rule: UfwRuleDict) -> List[str]:
    """Render a canonical rule dict back into ufw CLI tokens (without leading ``ufw``)."""

    action = rule.get("action") or ""
    direction = rule.get("direction")
    interface = rule.get("interface")
    from_ip = rule.get("from_")
    to_ip = rule.get("to")
    port = rule.get("port")
    proto = rule.get("proto")
    app = rule.get("app")
    log = rule.get("log")
    comment = rule.get("comment")

    # Short form: "ufw allow 22/tcp" rather than "ufw allow port 22 proto tcp".
    # UFW's `ufw show added` emits the short form, so using it here keeps the
    # rendered rule identical to what the parser sees when reading back.
    if (
        port
        and not from_ip
        and not to_ip
        and not interface
        and not direction
        and not app
        and not log
        and not comment
    ):
        port_token = "{0}/{1}".format(port, proto) if proto else port
        return [action, port_token]

    tokens: List[str] = []
    if direction == "route":
        tokens.append("route")

    tokens.append(action)

    if log:
        tokens.append(log)

    if direction in ("in", "out"):
        tokens.append(direction)  # type: ignore[arg-type]

    if interface:
        tokens += ["on", interface]

    if from_ip:
        tokens += ["from", from_ip]

    if to_ip:
        tokens += ["to", to_ip]

    if port:
        tokens += ["port", port]

    if proto:
        tokens += ["proto", proto]

    if app:
        tokens += ["app", app]

    if comment:
        escaped = comment.replace("'", "'\\''")
        tokens += ["comment", "'{0}'".format(escaped)]

    return tokens


# Explicit re-exports for type checkers / consumers.
__all__ = [
    "UfwRuleDict",
    "UfwRules",
    "UfwStatus",
    "UfwStatusDict",
    "_canonical_rule",
    "_parse_ufw_rule_line",
    "_render_rule",
]
