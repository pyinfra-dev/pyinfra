from typing import TYPE_CHECKING
from collections.abc import Callable

from pyinfra.context import host

if TYPE_CHECKING:
    from pyinfra.api.facts import FactBase, ShortFactBase
    from pyinfra.api.operation import OperationMeta


def any_changed(*args: "OperationMeta") -> Callable[[], bool]:
    return lambda: any(meta.did_change() for meta in args)


def all_changed(*args: "OperationMeta") -> Callable[[], bool]:
    return lambda: all(meta.did_change() for meta in args)


def any_fact(*facts: type["FactBase"] | type["ShortFactBase"]) -> Callable[[], bool]:
    """Return a condition that is true when any zero-argument fact is truthy."""
    return lambda: any(host.get_fact(fact) for fact in facts)


def all_fact(*facts: type["FactBase"] | type["ShortFactBase"]) -> Callable[[], bool]:
    """Return a condition that is true when all zero-argument facts are truthy."""
    return lambda: all(host.get_fact(fact) for fact in facts)
