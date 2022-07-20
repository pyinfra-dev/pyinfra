import typing
import pyinfra

def service(
    service,
    running=True,
    restarted=False,
    command=None,
    _sudo: typing.Optional[bool] = None,
    _sudo_user: typing.Optional[bool] = None,
    _use_sudo_login: typing.Optional[bool] = None,
    _use_sudo_password: typing.Optional[bool] = None,
    _preserve_sudo_env: typing.Optional[bool] = None,
    _su_user: typing.Optional[str] = None,
    _use_su_login: typing.Optional[bool] = None,
    _preserve_su_env: typing.Optional[bool] = None,
    _su_shell: typing.Optional[str] = None,
    _doas: typing.Optional[bool] = None,
    _doas_user: typing.Optional[str] = None,
    _shell_executable: typing.Optional[str] = None,
    _chdir: typing.Optional[str] = None,
    _env: typing.Optional[typing.Mapping[str, str]] = None,
    _success_exit_codes: typing.Optional[typing.Iterable[int]] = None,
    _timeout: typing.Optional[int] = None,
    _get_pty: typing.Optional[bool] = None,
    _stdin: typing.Optional[typing.Union[str, list, tuple]] = None,
    name: typing.Optional[str] = None,
    _ignore_errors: typing.Optional[bool] = None,
    _continue_on_error: typing.Optional[bool] = None,
    _precondition: typing.Optional[str] = None,
    _postcondition: typing.Optional[str] = None,
    _on_success: typing.Optional[
        typing.Callable[[pyinfra.api.state.State, pyinfra.api.host.Host, str], None]
    ] = None,
    _on_error: typing.Optional[
        typing.Callable[[pyinfra.api.state.State, pyinfra.api.host.Host, str], None]
    ] = None,
    _parallel: typing.Optional[int] = None,
    _run_once: typing.Optional[bool] = None,
    _serial: typing.Optional[bool] = None,
): ...
