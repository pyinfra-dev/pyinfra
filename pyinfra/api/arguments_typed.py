from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Callable,
    Generator,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Union,
)

from typing_extensions import ParamSpec, Protocol

if TYPE_CHECKING:
    from pyinfra.api.operation import OperationMeta

P = ParamSpec("P")


# Unfortunately we have to re-type out all of the global arguments here because
# Python typing doesn't (yet) support merging kwargs. This acts as the operation
# decorator output function which merges actual operation args/kwargs in paramspec
# with the global arguments available in all operations.
# The nature of "global arguments" is somewhat opposed to static typing as it's
# indirect and somewhat magic, but we are where we are.
class PyinfraOperation(Generic[P], Protocol):
    _inner: Callable[P, Generator]

    def __call__(
        self,
        #
        # ConnectorArguments
        #
        # Auth
        _sudo: bool = False,
        _sudo_user: Optional[str] = None,
        _use_sudo_login: bool = False,
        _sudo_password: Optional[str] = None,
        _preserve_sudo_env: bool = False,
        _su_user: Optional[str] = None,
        _use_su_login: bool = False,
        _preserve_su_env: bool = False,
        _su_shell: Optional[str] = None,
        _doas: bool = False,
        _doas_user: Optional[str] = None,
        # Shell arguments
        _shell_executable: Optional[str] = None,
        _chdir: Optional[str] = None,
        _env: Optional[Mapping[str, str]] = None,
        # Connector control
        _success_exit_codes: Iterable[int] = (0,),
        _timeout: Optional[int] = None,
        _get_pty: bool = False,
        _stdin: Union[None, str, list[str], tuple[str, ...]] = None,
        #
        # MetaArguments
        #
        name: Optional[str] = None,
        _ignore_errors: bool = False,
        _continue_on_error: bool = False,
        _if: Union[List[Callable[[], bool]], Callable[[], bool], None] = None,
        #
        # ExecutionArguments
        #
        _parallel: Optional[int] = None,
        _run_once: bool = False,
        _serial: bool = False,
        #
        # op args
        #
        *args: P.args,
        #
        # op kwargs
        #
        **kwargs: P.kwargs,
    ) -> "OperationMeta": ...
