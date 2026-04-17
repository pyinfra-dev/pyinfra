"""
Manage `ufw <https://launchpad.net/ufw>`_ (Uncomplicated Firewall) state and
rules. Operations read the :class:`pyinfra.facts.ufw.UfwStatus` and
:class:`pyinfra.facts.ufw.UfwRules` facts so that repeated runs are a noop
whenever the host already matches the desired state.
"""

from __future__ import annotations

from typing import Optional, Union

from pyinfra import host
from pyinfra.api import OperationError, operation
from pyinfra.facts.ufw import (
    UfwRules,
    UfwStatus,
    _canonical_rule,
    _render_rule,
)

_POLICIES = ("allow", "deny", "reject")
_DIRECTIONS = ("incoming", "outgoing", "routed")
_LOGGING_LEVELS = ("off", "on", "low", "medium", "high", "full")


@operation()
def service(enabled: bool = True, reload: bool = False):
    """
    Enable or disable the UFW service.

    + enabled: whether the firewall should be running
    + reload: also issue ``ufw reload`` when ``enabled`` is ``True`` and ufw is
      already active; this re-applies the rules without dropping the firewall

    ``enabled=True`` uses ``ufw --force enable`` so the operation never prompts
    for confirmation over SSH.

    **Example:**

    .. code:: python

        ufw.service(
            name="Enable ufw",
            enabled=True,
        )
    """

    status = host.get_fact(UfwStatus)
    is_active = bool(status.get("active"))

    if enabled:
        if is_active:
            if reload:
                yield "ufw reload"
            else:
                host.noop("ufw service is already enabled")
        else:
            yield "ufw --force enable"
    else:
        if is_active:
            yield "ufw disable"
        else:
            host.noop("ufw service is already disabled")


@operation()
def default(policy: str, direction: str = "incoming"):
    """
    Set the default policy for a traffic direction.

    + policy: one of ``allow``, ``deny`` or ``reject``
    + direction: one of ``incoming``, ``outgoing`` or ``routed``

    **Example:**

    .. code:: python

        ufw.default(
            name="Deny all inbound by default",
            policy="deny",
            direction="incoming",
        )
    """

    if policy not in _POLICIES:
        raise OperationError("policy must be one of {0}, got {1!r}".format(_POLICIES, policy))
    if direction not in _DIRECTIONS:
        raise OperationError(
            "direction must be one of {0}, got {1!r}".format(_DIRECTIONS, direction)
        )

    status = host.get_fact(UfwStatus)
    current = (status.get("default") or {}).get(direction)

    if current == policy:
        host.noop("ufw default {0} is already {1}".format(direction, policy))
        return

    yield "ufw default {0} {1}".format(policy, direction)


@operation()
def logging(level: Union[str, bool]):
    """
    Control the ufw logging level.

    + level: ``True`` / ``False`` (same as ``on``/``off``), or one of
      ``off``, ``on``, ``low``, ``medium``, ``high`` or ``full``

    **Example:**

    .. code:: python

        ufw.logging(
            name="Set ufw logging to low",
            level="low",
        )
    """

    if level is True:
        level = "on"
    elif level is False:
        level = "off"

    if not isinstance(level, str) or level not in _LOGGING_LEVELS:
        raise OperationError(
            "level must be one of {0} or bool, got {1!r}".format(_LOGGING_LEVELS, level)
        )

    status = host.get_fact(UfwStatus)
    current = status.get("logging")

    if level == "off":
        if current is None:
            host.noop("ufw logging is already off")
            return
    else:
        # When a specific level is requested, match on the level; "on" matches
        # any non-off current setting.
        if level == "on":
            if current is not None:
                host.noop("ufw logging is already on")
                return
        elif current == level:
            host.noop("ufw logging is already {0}".format(level))
            return

    yield "ufw logging {0}".format(level)


@operation()
def rule(
    action: str,
    port: Union[str, int, None] = None,
    proto: Optional[str] = None,
    from_ip: Optional[str] = None,
    to_ip: Optional[str] = None,
    direction: Optional[str] = None,
    interface: Optional[str] = None,
    app: Optional[str] = None,
    log: Union[bool, str, None] = False,
    comment: Optional[str] = None,
    present: bool = True,
):
    """
    Add or remove a ufw rule. Idempotent by structured match against
    :class:`pyinfra.facts.ufw.UfwRules`.

    + action: one of ``allow``, ``deny``, ``reject`` or ``limit``
    + port: port number or range (e.g. ``22`` or ``80:85``)
    + proto: ``tcp`` or ``udp``
    + from_ip: source address / subnet (or ``any``)
    + to_ip: destination address (or ``any``)
    + direction: ``in``, ``out`` or ``route``
    + interface: interface name (requires ``direction=in`` or ``out``)
    + app: ufw application profile name (mutually exclusive with port/proto)
    + log: ``True`` / ``"log"`` / ``"log-all"`` to enable logging for the rule
    + comment: optional comment attached to the rule
    + present: whether the rule should be present (``True``) or absent (``False``)

    **Examples:**

    .. code:: python

        ufw.rule(
            name="Allow SSH",
            action="allow",
            port=22,
            proto="tcp",
        )

        ufw.rule(
            name="Drop noisy peer",
            action="deny",
            from_ip="203.0.113.5",
            present=False,
        )
    """

    log_value: Optional[str]
    if log is True:
        log_value = "log"
    elif log is False or log is None:
        log_value = None
    else:
        log_value = log

    target = _canonical_rule(
        action=action,
        direction=direction,
        interface=interface,
        from_ip=from_ip,
        to_ip=to_ip,
        port=str(port) if port is not None else None,
        proto=proto,
        app=app,
        log=log_value,
        comment=comment,
    )

    existing = host.get_fact(UfwRules)
    exists = target in existing

    if present:
        if exists:
            host.noop("ufw rule is already present")
            return
        tokens = _render_rule(target)
        yield " ".join(["ufw"] + tokens)
    else:
        if not exists:
            host.noop("ufw rule is already absent")
            return
        tokens = _render_rule(target)
        yield " ".join(["ufw", "delete"] + tokens)
