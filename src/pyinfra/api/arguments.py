from __future__ import annotations

import os
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    cast,
    get_type_hints,
)
from collections.abc import Callable, Iterable, Mapping

from typing_extensions import TypedDict

from pyinfra.api.exceptions import ArgumentTypeError
from pyinfra.api.util import raise_if_bad_type
from pyinfra.context import ctx_config
from pyinfra.api.hiddenvalue import HiddenValue

if TYPE_CHECKING:
    from pyinfra.api import Config, Host, State

T = TypeVar("T")
default_sentinel = object()

EnvValue = str | HiddenValue


class ArgumentMeta(Generic[T]):
    description: str
    default: Callable[[Config], T]
    handler: Callable[[Config, T], T] | None

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
    _su_password: str
    _doas: bool
    _doas_user: str
    _dzdo: bool
    _dzdo_user: str

    # Shell arguments
    _shell_executable: str
    _chdir: str
    _env: Mapping[str, EnvValue]

    # Connector control (outside of command generation)
    _success_exit_codes: Iterable[int]
    _timeout: int
    _get_pty: bool
    _stdin: str | list[str] | Iterable[str]

    # Retry arguments
    _retries: int
    _retry_delay: int | float
    _retry_until: Callable[[dict], bool]

    # Temp directory argument
    _temp_dir: str


def generate_env(config: Config, value: Mapping[str, EnvValue] | None) -> dict[str, EnvValue]:
    env: dict[str, EnvValue] = {
        key: os.environ[key] for key in config.INHERIT_ENV if key in os.environ
    }
    env.update(config.ENV)
    if value is not None:
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
    "_su_password": ArgumentMeta(
        "Password to su with.",
        default=lambda config: config.SU_PASSWORD,
    ),
    "_doas": ArgumentMeta(
        "Execute/apply any changes with doas.",
        default=lambda config: config.DOAS,
    ),
    "_doas_user": ArgumentMeta(
        "Execute/apply any changes with doas as a non-root user.",
        default=lambda config: config.DOAS_USER,
    ),
    "_dzdo": ArgumentMeta(
        "Execute/apply any changes with dzdo.",
        default=lambda config: config.DZDO,
    ),
    "_dzdo_user": ArgumentMeta(
        "Execute/apply any changes with dzdo as a non-root user.",
        default=lambda config: config.DZDO_USER,
    ),
}

shell_argument_meta: dict[str, ArgumentMeta] = {
    "_shell_executable": ArgumentMeta(
        "The shell executable to use for executing commands.",
        default=lambda config: config.SHELL,
    ),
    "_chdir": ArgumentMeta(
        "Directory to switch to before executing the command.",
        default=lambda _: None,
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
    "_temp_dir": ArgumentMeta(
        "Temporary directory on the remote host for file operations.",
        default=lambda config: config.TEMP_DIR,
    ),
}


# Meta arguments
# These provide/extend additional operation metadata


class MetaArguments(TypedDict):
    name: str
    _ignore_errors: bool
    _continue_on_error: bool
    _if: list[Callable[[], bool]] | Callable[[], bool] | None


meta_argument_meta: dict[str, ArgumentMeta] = {
    # NOTE: name is the only non-_-prefixed argument
    "name": ArgumentMeta(
        (
            "Human-readable label for the operation, shown in CLI output and used to identify "
            "the operation in the execution order. Does not affect what is run. If omitted, "
            "pyinfra generates a label from the operation's call signature."
        ),
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
        "Only run this operation if these functions return True",
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
        (
            "Maximum number of hosts to execute this operation on at once. ``0`` (the default) "
            "means use the global ``config.PARALLEL`` value, which itself defaults to *all hosts "
            "in parallel*, capped by the system's open-file-descriptor limit."
        ),
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


def all_global_arguments() -> list[tuple[str, type]]:
    """Return all global arguments and their types."""
    return list(get_type_hints(AllArguments).items())


# Create a dictionary for retry arguments
retry_argument_meta: dict[str, ArgumentMeta] = {
    "_retries": ArgumentMeta(
        "Number of times to retry failed operations.",
        default=lambda config: config.RETRY,
    ),
    "_retry_delay": ArgumentMeta(
        "Delay in seconds between retry attempts.",
        default=lambda config: config.RETRY_DELAY,
    ),
    "_retry_until": ArgumentMeta(
        "Callable taking output data that returns True to continue retrying.",
        default=lambda config: None,
    ),
}

all_argument_meta: dict[str, ArgumentMeta] = {
    **auth_argument_meta,
    **shell_argument_meta,
    **meta_argument_meta,
    **execution_argument_meta,
    **retry_argument_meta,  # Add retry arguments
}

EXECUTION_KWARG_KEYS = list(ExecutionArguments.__annotations__.keys())
CONNECTOR_ARGUMENT_KEYS = list(ConnectorArguments.__annotations__.keys())

__argument_docs__ = {
    "Privilege & user escalation": (
        auth_argument_meta,
        """
        .. caution::
            When combining privilege escalation arguments it is important to know the order they
            are applied: ``doas`` -> ``dzdo`` -> ``sudo`` -> ``su``. For example
            ``_sudo=True,_su_user="pyinfra"`` yields a command like ``sudo su pyinfra..``.
        """,
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
        "",
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
    "Operation meta & callbacks": (meta_argument_meta, "", ""),
    "Execution strategy": (
        execution_argument_meta,
        """
        By default, every operation runs against **all hosts in parallel** (capped by the open-file
        limit). ``_parallel`` lowers that cap for a single operation, ``_serial`` forces host-by-host
        execution, and ``_run_once`` executes only against the first host that reaches the operation.
        These three are mutually exclusive on a per-operation basis and must take the same value on
        every host.
        """,
        "",
    ),
    "Retry behavior": (
        retry_argument_meta,
        """
        Retry arguments allow you to automatically retry operations that fail. You can specify
        how many times to retry, the delay between retries, and optionally a condition
        function to determine when to stop retrying.
        """,
        """
        .. code:: python

            # Retry a command up to 3 times with the default 5 second delay
            server.shell(
                name="Run flaky command with retries",
                commands=["flaky_command"],
                _retries=3,
            )
            # Retry with a custom delay
            server.shell(
                name="Run flaky command with custom delay",
                commands=["flaky_command"],
                _retries=2,
                _retry_delay=10,  # 10 second delay between retries
            )
            # Retry with a custom condition
            def retry_on_specific_error(output_data):
                # Retry if stderr contains "temporary failure"
                for line in output_data["stderr_lines"]:
                    if "temporary failure" in line.lower():
                        return True
                return False

            server.shell(
                name="Run command with conditional retry",
                commands=["flaky_command"],
                _retries=5,
                _retry_until=retry_on_specific_error,
            )
        """,
    ),
}


def pop_global_arguments(
    state: State,
    host: Host,
    kwargs: dict[str, Any],
) -> tuple[AllArguments, list[str]]:
    """
    Pop and return operation global keyword arguments, in preferred order:

    + From the current context (a direct @operator or @deploy function being called)
    + From any current @deploy context (deploy kwargs)
    + From the host data variables
    + From the config variables
    """

    config = state.config
    if ctx_config.isset():
        config = ctx_config.get()
        assert config is not None

    cdkwargs = host.current_deploy_kwargs
    meta_kwargs: dict[str, Any] = cdkwargs or {}  # type: ignore[assignment]

    arguments: dict[str, Any] = {}
    found_keys: list[str] = []

    for key, type_ in all_global_arguments():
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
