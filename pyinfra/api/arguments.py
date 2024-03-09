from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    TypeVar,
    Union,
    cast,
    get_type_hints,
)

from typing_extensions import TypedDict

from pyinfra import context
from pyinfra.api.exceptions import ArgumentTypeError
from pyinfra.api.state import State
from pyinfra.api.util import raise_if_bad_type

if TYPE_CHECKING:
    from pyinfra.api.config import Config
    from pyinfra.api.host import Host

T = TypeVar("T")
default_sentinel = object()


class ArgumentMeta(Generic[T]):
    description: str
    default: Callable[["Config"], T]
    handler: Optional[Callable[["Config", T], T]]

    def __init__(self, description, default, handler=None) -> None:
        self.description = description
        self.default = default
        self.handler = handler


# Connector arguments
# These are arguments passed to the various connectors that provide the underlying
# API to read/write external systems.


# Note: ConnectorArguments is specifically not total as it's used to type many
# functions via Unpack and we don't want to specify every kwarg.
class ConnectorArguments(TypedDict, total=False):
    # Auth arguments
    _sudo: bool
    _sudo_user: str
    _use_sudo_login: bool
    _sudo_password: str
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
    _stdin: Union[str, Iterable[str]]


def generate_env(config: "Config", value: dict) -> dict:
    env = config.ENV.copy()
    env.update(value)
    return env


auth_argument_meta: dict[str, ArgumentMeta] = {
    "_sudo": ArgumentMeta(
        "Execute/apply any changes with sudo.",
        default=lambda config: config.SUDO,
    ),
    "_sudo_user": ArgumentMeta(
        "Execute/apply any changes with sudo as a non-root user.",
        default=lambda config: config.SUDO_USER,
    ),
    "_use_sudo_login": ArgumentMeta(
        "Execute sudo with a login shell.",
        default=lambda config: config.USE_SUDO_LOGIN,
    ),
    "_sudo_password": ArgumentMeta(
        "Password to sudo with. If needed and not specified pyinfra will prompt for it.",
        default=lambda config: config.SUDO_PASSWORD,
    ),
    "_preserve_sudo_env": ArgumentMeta(
        "Preserve the shell environment of the connecting user when using sudo.",
        default=lambda config: config.PRESERVE_SUDO_ENV,
    ),
    "_su_user": ArgumentMeta(
        "Execute/apply any changes with this user using su.",
        default=lambda config: config.SU_USER,
    ),
    "_use_su_login": ArgumentMeta(
        "Execute su with a login shell.",
        default=lambda config: config.USE_SU_LOGIN,
    ),
    "_preserve_su_env": ArgumentMeta(
        "Preserve the shell environment of the connecting user when using su.",
        default=lambda config: config.PRESERVE_SU_ENV,
    ),
    "_su_shell": ArgumentMeta(
        "Use this shell (instead of user login shell) when using ``_su``). "
        + "Only available under Linux, for use when using `su` with a user that "
        + "has nologin/similar as their login shell.",
        default=lambda config: config.SU_SHELL,
    ),
    "_doas": ArgumentMeta(
        "Execute/apply any changes with doas.",
        default=lambda config: config.DOAS,
    ),
    "_doas_user": ArgumentMeta(
        "Execute/apply any changes with doas as a non-root user.",
        default=lambda config: config.DOAS_USER,
    ),
}

shell_argument_meta: dict[str, ArgumentMeta] = {
    "_shell_executable": ArgumentMeta(
        "The shell executable to use for executing commands.",
        default=lambda config: config.SHELL,
    ),
    "_chdir": ArgumentMeta(
        "Directory to switch to before executing the command.",
        default=lambda _: "",
    ),
    "_env": ArgumentMeta(
        "Dictionary of environment variables to set.",
        default=lambda _: {},
        handler=generate_env,
    ),
    "_success_exit_codes": ArgumentMeta(
        "List of exit codes to consider a success.",
        default=lambda _: [0],
    ),
    "_timeout": ArgumentMeta(
        "Timeout for *each* command executed during the operation.",
        default=lambda _: None,
    ),
    "_get_pty": ArgumentMeta(
        "Whether to get a pseudoTTY when executing any commands.",
        default=lambda _: False,
    ),
    "_stdin": ArgumentMeta(
        "String or buffer to send to the stdin of any commands.",
        default=lambda _: None,
    ),
}


# Meta arguments
# These provide/extend additional operation metadata


class MetaArguments(TypedDict):
    name: str
    _ignore_errors: bool
    _continue_on_error: bool
    _if: List[Callable[[], bool]]


meta_argument_meta: dict[str, ArgumentMeta] = {
    # NOTE: name is the only non-_-prefixed argument
    "name": ArgumentMeta(
        "Name of the operation.",
        default=lambda _: None,
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
        default=lambda _: False,
    ),
    "_if": ArgumentMeta(
        "Only run this operation if these functions returns True",
        default=lambda _: [],
    ),
}


# Execution arguments
# These alter how pyinfra is to execute an operation. Notably these must all have the same value
# over every target host for the same operation.


class ExecutionArguments(TypedDict):
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
        default=lambda _: False,
    ),
    "_serial": ArgumentMeta(
        "Run this operation host by host, rather than in parallel.",
        default=lambda _: False,
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

EXECUTION_KWARG_KEYS = list(ExecutionArguments.__annotations__.keys())
CONNECTOR_ARGUMENT_KEYS = list(ConnectorArguments.__annotations__.keys())

__argument_docs__ = {
    "Privilege & user escalation": (
        auth_argument_meta,
        """
        .. code:: python

            # Execute a command with sudo
            server.user(
                name="Create pyinfra user using sudo",
                user="pyinfra",
                _sudo=True,
            )

            # Execute a command with a specific sudo password
            server.user(
                name="Create pyinfra user using sudo",
                user="pyinfra",
                _sudo=True,
                _sudo_password="my-secret-password",
            )
        """,
    ),
    "Shell control & features": (
        shell_argument_meta,
        """
        .. code:: python

            # Execute from a specific directory
            server.shell(
                name="Bootstrap nginx params",
                commands=["openssl dhparam -out dhparam.pem 4096"],
                _chdir="/etc/ssl/certs",
            )
        """,
    ),
    "Operation meta & callbacks": (meta_argument_meta, ""),
    "Execution strategy": (execution_argument_meta, ""),
}


def pop_global_arguments(
    kwargs: dict[str, Any],
    state: Optional["State"] = None,
    host: Optional["Host"] = None,
    keys_to_check=None,
) -> tuple[AllArguments, list[str]]:
    """
    Pop and return operation global keyword arguments, in preferred order:

    + From the current context (a direct @operator or @deploy function being called)
    + From any current @deploy context (deploy kwargs)
    + From the host data variables
    + From the config variables
    """

    state = state or context.state
    host = host or context.host

    config = state.config
    if context.ctx_config.isset():
        config = context.config

    meta_kwargs: dict[str, Any] = host.current_deploy_kwargs or {}  # type: ignore[assignment]

    arguments: dict[str, Any] = {}
    found_keys: list[str] = []

    for key, type_ in get_type_hints(AllArguments).items():
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

        if handler:
            value = handler(config, value)

        if value != default:
            raise_if_bad_type(
                value,
                type_,
                ArgumentTypeError,
                f"Invalid argument `{key}`:",
            )

        # TODO: why is type failing here?
        arguments[key] = value  # type: ignore
    return cast(AllArguments, arguments), found_keys
