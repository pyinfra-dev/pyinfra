from typing import Any, Callable, Optional

OPERATIONS: Any


def get_operation_names():
    ...


class OperationMeta:
    commands: Any = ...
    hash: Any = ...
    changed: Any = ...

    def __init__(self, hash: Optional[Any] = ..., commands: Optional[Any] = ...) -> None:
        ...


def add_op(state: Any, op_func: Any, *args: Any, **kwargs: Any):
    ...


def show_set_name_warning(call_location: Any) -> None:
    ...


def show_state_host_arguments_warning(call_location: Any) -> None:
    ...


def operation(func: Optional[Callable[..., Any]] = ..., pipeline_facts: Optional[Any] = ...):
    ...
