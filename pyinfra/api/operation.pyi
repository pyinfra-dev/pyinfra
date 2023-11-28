import abc
from typing import (
    Callable,
    Dict,
    Generator,
    Generic,
    Iterable,
    List,
    Mapping,
    Protocol,
    Tuple,
    overload,
)

from typing_extensions import ParamSpec

from pyinfra.api.command import (
    FileDownloadCommand,
    FileUploadCommand,
    FunctionCommand,
    StringCommand,
)
from pyinfra.api.host import Host
from pyinfra.api.state import State

P = ParamSpec("P")

Command = str | StringCommand | FileDownloadCommand | FileUploadCommand | FunctionCommand

class OperationMeta(Generator, metaclass=abc.ABCMeta):
    changed: bool
    commands: List[str] | None
    hash: str | None

    stdout_lines: List[str]
    stdout: str
    stderr_lines: List[str]
    stderr: str

class Operation(Generic[P], Protocol):
    def __call__(
        self,
        _sudo: bool | None = None,
        _sudo_user: str | None = None,
        _use_sudo_login: bool | None = None,
        _use_sudo_password: bool | None = None,
        _preserve_sudo_env: bool | None = None,
        _su_user: str | None = None,
        _use_su_login: bool | None = None,
        _preserve_su_env: bool | None = None,
        _su_shell: str | None = None,
        _doas: bool | None = None,
        _doas_user: str | None = None,
        _shell_executable: str | None = None,
        _chdir: str | None = None,
        _env: Mapping[str, str] | None = None,
        _success_exit_codes: Iterable[int] | None = None,
        _timeout: int | None = None,
        _get_pty: bool | None = None,
        _stdin: str | List[str] | Tuple[str, ...] | None = None,
        name: str | None = None,
        _ignore_errors: bool | None = None,
        _continue_on_error: bool | None = None,
        _on_success: Callable[[State, Host, str], None] | None = None,
        _on_error: Callable[[State, Host, str], None] | None = None,
        _parallel: int | None = None,
        _run_once: bool | None = None,
        _serial: bool | None = None,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> OperationMeta: ...

def add_op(
    state: State,
    op_func: Operation[P],
    _sudo: bool | None = None,
    _sudo_user: str | None = None,
    _use_sudo_login: bool | None = None,
    _use_sudo_password: bool | None = None,
    _preserve_sudo_env: bool | None = None,
    _su_user: str | None = None,
    _use_su_login: bool | None = None,
    _preserve_su_env: bool | None = None,
    _su_shell: str | None = None,
    _doas: bool | None = None,
    _doas_user: str | None = None,
    _shell_executable: str | None = None,
    _chdir: str | None = None,
    _env: Mapping[str, str] | None = None,
    _success_exit_codes: Iterable[int] | None = None,
    _timeout: int | None = None,
    _get_pty: bool | None = None,
    _stdin: str | List[str] | Tuple[str, ...] | None = None,
    name: str | None = None,
    _ignore_errors: bool | None = None,
    _continue_on_error: bool | None = None,
    _on_success: Callable[[State, Host, str], None] | None = None,
    _on_error: Callable[[State, Host, str], None] | None = None,
    _parallel: int | None = None,
    _run_once: bool | None = None,
    _serial: bool | None = None,
    host: Iterable[Host] | Host | None = None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> Dict[Host, OperationMeta]: ...

# Operation decorator
def operation(
    pipeline_facts=None,
    is_idempotent: bool = True,
    idempotent_notice=None,
    frame_offset=1,
) -> Callable[[Callable[P, Generator[Command, None, None]]], Operation[P]]: ...
