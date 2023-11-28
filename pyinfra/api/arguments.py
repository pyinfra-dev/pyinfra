from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterable, Mapping, Optional, Tuple, TypeVar, Union

from typing_extensions import TypedDict

from pyinfra import context
from pyinfra.api.state import State

from .util import memoize

if TYPE_CHECKING:
    from pyinfra.api.config import Config
    from pyinfra.api.host import Host


T = TypeVar("T")


default_sentinel = object()


class ArgumentMeta:
    description: str
    default: Callable[["Config"], T]
    handler: Callable[["Config", T], T]

    def __init__(self, description, default, handler=default_sentinel) -> None:
        self.description = description
        self.default = default
        self.handler = handler


# Connector arguments
# These are arguments passed to the various connectors that provide the underlying
# API to read/write external systems.


class ConnectorArguments(TypedDict, total=False):
    # Auth arguments
    _sudo: bool
    _sudo_user: str
    _use_sudo_login: bool
    _use_sudo_password: bool
    _preserve_sudo_env: bool
    _su_user: str
    _use_su_login: bool
    _preserve_su_env: bool
    _su_shell: str
    _doas: bool
    _doas_user: str

    # Shell arguments
    _shell_executable: str
    _chdir: str
    _env: Mapping[str, str]

    # Connector control (outside of command generation)
    _success_exit_codes: Iterable[int]
    _timeout: int
    _get_pty: bool
    _stdin: Union[str, list, tuple]


def generate_env(config: "Config", value: dict) -> dict:
    env = config.ENV.copy()
    env.update(value)
    return env


auth_argument_meta: dict[str, ArgumentMeta] = {
    "_sudo": ArgumentMeta(
        "Execute/apply any changes with ``sudo``.",
        default=lambda config: config.SUDO,
    ),
    "_sudo_user": ArgumentMeta(
        "Execute/apply any changes with ``sudo`` as a non-root user.",
        default=lambda config: config.SUDO_USER,
    ),
    "_use_sudo_login": ArgumentMeta(
        "Execute ``sudo`` with a login shell.",
        default=lambda config: config.USE_SUDO_LOGIN,
    ),
    "_use_sudo_password": ArgumentMeta(
        "Whether to use a password with ``sudo`` (will ask).",
        default=lambda config: config.USE_SUDO_PASSWORD,
    ),
    "_preserve_sudo_env": ArgumentMeta(
        "Preserve the shell environment when using ``sudo``.",
        default=lambda config: config.PRESERVE_SUDO_ENV,
    ),
    "_su_user": ArgumentMeta(
        "Execute/apply any changes with this user using ``su``.",
        default=lambda config: config.SU_USER,
    ),
    "_use_su_login": ArgumentMeta(
        "Execute ``su`` with a login shell.",
        default=lambda config: config.USE_SU_LOGIN,
    ),
    "_preserve_su_env": ArgumentMeta(
        "Preserve the shell environment when using ``su``.",
        default=lambda config: config.PRESERVE_SU_ENV,
    ),
    "_su_shell": ArgumentMeta(
        "Use this shell (instead of user login shell) when using ``su``). "
        "Only available under Linux, for use when using `su` with a user that "
        "has nologin/similar as their login shell.",
        default=lambda config: config.SU_SHELL,
    ),
    "_doas": ArgumentMeta(
        "Execute/apply any changes with ``doas``.",
        default=lambda config: config.DOAS,
    ),
    "_doas_user": ArgumentMeta(
        "Execute/apply any changes with ``doas`` as a non-root user.",
        default=lambda config: config.DOAS_USER,
    ),
}

shell_argument_meta: dict[str, ArgumentMeta] = {
    "_shell_executable": ArgumentMeta(
        "The shell to use. Defaults to ``sh`` (Unix) or ``cmd`` (Windows).",
        default=lambda config: config.SHELL,
    ),
    "_chdir": ArgumentMeta(
        "Directory to switch to before executing the command.",
        default=lambda config: "",
    ),
    "_env": ArgumentMeta(
        "Dictionary of environment variables to set.",
        default=lambda config: {},
        handler=generate_env,
    ),
    "_success_exit_codes": ArgumentMeta(
        "List of exit codes to consider a success.",
        default=lambda config: [0],
    ),
    "_timeout": ArgumentMeta(
        "Timeout for *each* command executed during the operation.",
        default=lambda config: None,
    ),
    "_get_pty": ArgumentMeta(
        "Whether to get a pseudoTTY when executing any commands.",
        default=lambda config: False,
    ),
    "_stdin": ArgumentMeta(
        "String or buffer to send to the stdin of any commands.",
        default=lambda config: None,
    ),
}


# Meta arguments
# These provide/extend additional operation metadata


class MetaArguments(TypedDict, total=False):
    name: str
    _ignore_errors: bool
    _continue_on_error: bool
    _on_success: Callable[[State, "Host", str], None]
    _on_error: Callable[[State, "Host", str], None]


meta_argument_meta: dict[str, ArgumentMeta] = {
    # NOTE: name is the only non-_-prefixed argument
    "name": ArgumentMeta(
        "Name of the operation.",
        default=lambda config: None,
    ),
    "_ignore_errors": ArgumentMeta(
        "Ignore errors when executing the operation.",
        default=lambda config: config.IGNORE_ERRORS,
    ),
    "_continue_on_error": ArgumentMeta(
        (
            "Continue executing operation commands after error. "
            "Only applies when ``_ignore_errors`` is true."
        ),
        default=lambda config: False,
    ),
    # Lambda on the next two are to workaround a circular import
    "_on_success": ArgumentMeta(
        "Callback function to execute on success.",
        default=lambda config: None,
    ),
    "_on_error": ArgumentMeta(
        "Callback function to execute on error.",
        default=lambda config: None,
    ),
}


# Execution arguments
# These alter how pyinfra is to execute an operation. Notably these must all have the same value
# over every target host for the same operation.


class ExecutionArguments(TypedDict, total=False):
    _parallel: int
    _run_once: bool
    _serial: bool


execution_argument_meta: dict[str, ArgumentMeta] = {
    "_parallel": ArgumentMeta(
        "Run this operation in batches of hosts.",
        default=lambda config: config.PARALLEL,
    ),
    "_run_once": ArgumentMeta(
        "Only execute this operation once, on the first host to see it.",
        default=lambda config: False,
    ),
    "_serial": ArgumentMeta(
        "Run this operation host by host, rather than in parallel.",
        default=lambda config: False,
    ),
}


class AllArguments(ConnectorArguments, MetaArguments, ExecutionArguments):
    pass


all_argument_meta: dict[str, ArgumentMeta] = {
    **auth_argument_meta,
    **shell_argument_meta,
    **meta_argument_meta,
    **execution_argument_meta,
}


OPERATION_KWARG_DOC: list[tuple[str, Optional[str], type, dict[str, ArgumentMeta]]] = [
    ("Privilege & user escalation", None, ConnectorArguments, auth_argument_meta),
    ("Shell control & features", None, ConnectorArguments, shell_argument_meta),
    ("Operation meta & callbacks", "Not available in facts.", MetaArguments, meta_argument_meta),
    (
        "Execution strategy",
        "Not available in facts, value must be the same for all hosts.",
        ExecutionArguments,
        execution_argument_meta,
    ),
]


# Called ONCE to dedupe args that must be same for all calls of an op
@memoize
def get_execution_kwarg_keys() -> list[str]:
    return list(ExecutionArguments.__annotations__.keys())


@memoize
def get_connector_argument_keys() -> list[str]:
    return list(ConnectorArguments.__annotations__.keys())


def pop_global_arguments(
    kwargs: dict[str, Any],
    state: Optional["State"] = None,
    host: Optional["Host"] = None,
    keys_to_check=None,
) -> Tuple[AllArguments, list[str]]:
    """
    Pop and return operation global keyword arguments, in preferred order:

    + From the current context (a direct @operator or @deploy function being called)
    + From any current @deploy context (deploy kwargs)
    + From the host data variables
    + From the config variables

    Note this function is only called directly in the @operation & @deploy decorator
    wrappers which the user should pass global arguments prefixed "_". This is to
    avoid any clashes with operation and deploy functions both internal and third
    party.

    This is a bit strange because internally pyinfra uses non-_-prefixed arguments,
    and this function is responsible for the translation between the two.

    TODO: is this weird-ness acceptable? Is it worth updating internal use to _prefix?
    """

    state = state or context.state
    host = host or context.host

    config = state.config
    if context.ctx_config.isset():
        config = context.config

    meta_kwargs = host.current_deploy_kwargs or {}

    arguments: AllArguments = {}
    found_keys: list[str] = []

    for key, type_ in AllArguments.__annotations__.items():
        if keys_to_check and key not in keys_to_check:
            continue

        argument_meta = all_argument_meta[key]
        handler = argument_meta.handler
        default: Any = argument_meta.default(config)

        host_default = getattr(host.data, key, default_sentinel)
        if host_default is not default_sentinel:
            default = host_default

        if key in kwargs:
            found_keys.append(key)
            value = kwargs.pop(key)
        else:
            value = meta_kwargs.get(key, default)

        if handler is not default_sentinel:
            value = handler(config, value)

        # TODO: why is type failing here?
        arguments[key] = value  # type: ignore
    return arguments, found_keys
