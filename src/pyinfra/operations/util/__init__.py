from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from pyinfra.api.operation import OperationMeta


def any_changed(*args: "OperationMeta") -> Callable[[], bool]:
    return lambda: any((meta.did_change() for meta in args))


def all_changed(*args: "OperationMeta") -> Callable[[], bool]:
    return lambda: all((meta.did_change() for meta in args))
