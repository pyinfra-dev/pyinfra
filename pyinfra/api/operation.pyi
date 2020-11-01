from typing import Any, Callable, TypeVar

_TFunc = TypeVar("_TFunc", bound=Callable[..., Any])


def operation(func: _TFunc = None, pipeline_facts=None, name: str = None) -> _TFunc:
    ...
