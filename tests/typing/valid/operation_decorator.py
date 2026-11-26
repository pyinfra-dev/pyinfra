# Checked with: mypy --disallow-any-expr --follow-imports=silent tests/typing/valid/operation_decorator.py
from collections.abc import Generator

from pyinfra.api import StringCommand, operation


@operation()
def generator_operation(path: str) -> Generator[StringCommand | str, None, None]:
    yield StringCommand("touch", path)
    yield "echo done"


generator_operation(path="/tmp/file", _sudo=True)
