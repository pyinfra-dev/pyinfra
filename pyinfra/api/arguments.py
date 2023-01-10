from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Union,
)

import pyinfra
from pyinfra import context, logger
from pyinfra.api.state import State

from .util import get_call_location, memoize

if TYPE_CHECKING:
    from pyinfra.api.config import Config
    from pyinfra.api.host import Host

auth_kwargs = {
    "_sudo": {
        "description": "Execute/apply any changes with ``sudo``.",
        "default": lambda config: config.SUDO,
        "type": bool,
    },
    "_sudo_user": {
        "description": "Execute/apply any changes with ``sudo`` as a non-root user.",
        "default": lambda config: config.SUDO_USER,
        "type": str,
    },
    "_use_sudo_login": {
        "description": "Execute ``sudo`` with a login shell.",
        "default": lambda config: config.USE_SUDO_LOGIN,
        "type": bool,
    },
    "_use_sudo_password": {
        "description": "Whether to use a password with ``sudo`` (will ask).",
        "default": lambda config: config.USE_SUDO_PASSWORD,
        "type": bool,
    },
    "_preserve_sudo_env": {
        "description": "Preserve the shell environment when using ``sudo``.",
        "default": lambda config: config.PRESERVE_SUDO_ENV,
        "type": bool,
    },
    "_su_user": {
        "description": "Execute/apply any changes with this user using ``su``.",
        "default": lambda config: config.SU_USER,
        "type": str,
    },
    "_use_su_login": {
        "description": "Execute ``su`` with a login shell.",
        "default": lambda config: config.USE_SU_LOGIN,
        "type": bool,
    },
    "_preserve_su_env": {
        "description": "Preserve the shell environment when using ``su``.",
        "default": lambda config: config.PRESERVE_SU_ENV,
        "type": bool,
    },
    "_su_shell": {
        "description": (
            "Use this shell (instead of user login shell) when using ``su``). "
            "Only available under Linux, for use when using `su` with a user that "
            "has nologin/similar as their login shell."
        ),
        "default": lambda config: config.SU_SHELL,
        "type": str,
    },
    "_doas": {
        "description": "Execute/apply any changes with ``doas``.",
        "default": lambda config: config.DOAS,
        "type": bool,
    },
    "_doas_user": {
        "description": "Execute/apply any changes with ``doas`` as a non-root user.",
        "default": lambda config: config.DOAS_USER,
        "type": str,
    },
}


def generate_env(config: "Config", value):
    env = config.ENV.copy()

    # TODO: this is to protect against host.data.env being a string or similar,
    # the introduction of using host.data.X for operation kwargs combined with
    # `env` being a commonly defined data variable causes issues.
    # The real fix here is the prefixed `_env` argument.
    if value and isinstance(value, dict):
        env.update(value)

    return env


shell_kwargs = {
    "_shell_executable": {
        "description": "The shell to use. Defaults to ``sh`` (Unix) or ``cmd`` (Windows).",
        "default": lambda config: config.SHELL,
        "type": str,
    },
    "_chdir": {
        "description": "Directory to switch to before executing the command.",
        "type": str,
    },
    "_env": {
        "description": "Dictionary of environment variables to set.",
        "handler": generate_env,
        "type": Mapping[str, str],
    },
    "_success_exit_codes": {
        "description": "List of exit codes to consider a success.",
        "default": lambda config: [0],
        "type": Iterable[int],
    },
    "_timeout": {
        "description": "Timeout for *each* command executed during the operation.",
        "type": int,
    },
    "_get_pty": {
        "description": "Whether to get a pseudoTTY when executing any commands.",
        "type": bool,
    },
    "_stdin": {
        "description": "String or buffer to send to the stdin of any commands.",
        "type": Union[str, list, tuple],
    },
}

meta_kwargs = {
    # NOTE: name is the only non-_-prefixed argument
    "name": {
        "description": "Name of the operation.",
        "type": str,
    },
    "_ignore_errors": {
        "description": "Ignore errors when executing the operation.",
        "default": lambda config: config.IGNORE_ERRORS,
        "type": bool,
    },
    "_continue_on_error": {
        "description": (
            "Continue executing operation commands after error. "
            "Only applies when ``_ignore_errors`` is true."
        ),
        "default": False,
        "type": bool,
    },
    "_precondition": {
        "description": "Command to execute & check before the operation commands begin.",
        "type": str,
    },
    "_postcondition": {
        "description": "Command to execute & check after the operation commands complete.",
        "type": str,
    },
    # Lambda on the next two are to workaround a circular import
    "_on_success": {
        "description": "Callback function to execute on success.",
        "type": lambda: Callable[[State, pyinfra.api.Host, str], None],
    },
    "_on_error": {
        "description": "Callback function to execute on error.",
        "type": lambda: Callable[[State, pyinfra.api.Host, str], None],
    },
}

# Execution kwargs are global - ie must be identical for every host
execution_kwargs = {
    "_parallel": {
        "description": "Run this operation in batches of hosts.",
        "default": lambda config: config.PARALLEL,
        "type": int,
    },
    "_run_once": {
        "description": "Only execute this operation once, on the first host to see it.",
        "default": lambda config: False,
        "type": bool,
    },
    "_serial": {
        "description": "Run this operation host by host, rather than in parallel.",
        "default": lambda config: False,
        "type": bool,
    },
}

# TODO: refactor these into classes so they can be typed properly, remove Any
ALL_ARGUMENTS: Dict[str, Dict[str, Any]] = {
    **auth_kwargs,
    **shell_kwargs,
    **meta_kwargs,
    **execution_kwargs,
}

OPERATION_KWARG_DOC: List[Tuple[str, Optional[str], Dict[str, Dict[str, Any]]]] = [
    ("Privilege & user escalation", None, auth_kwargs),
    ("Shell control & features", None, shell_kwargs),
    ("Operation meta & callbacks", "Not available in facts.", meta_kwargs),
    (
        "Execution strategy",
        "Not available in facts, value must be the same for all hosts.",
        execution_kwargs,
    ),
]


def _get_internal_key(key: str) -> str:
    if key.startswith("_"):
        return key[1:]
    return key


@memoize
def get_execution_kwarg_keys() -> List[Any]:
    return [_get_internal_key(key) for key in execution_kwargs.keys()]


@memoize
def get_executor_kwarg_keys() -> List[Any]:
    keys: Set[str] = set()
    keys.update(auth_kwargs.keys(), shell_kwargs.keys())
    return [_get_internal_key(key) for key in keys]


@memoize
def show_legacy_argument_warning(key, call_location):
    logger.warning(
        (
            '{0}:\n\tGlobal arguments should be prefixed "_", '
            "please us the `{1}` keyword argument in place of `{2}`."
        ).format(call_location, "_{0}".format(key), key),
    )


@memoize
def show_legacy_argument_host_data_warning(key):
    logger.warning(
        (
            'Global arguments should be prefixed "_", '
            "please us the `host.data._{0}` keyword argument in place of `host.data.{0}`."
        ).format(key),
    )


def pop_global_arguments(
    kwargs: Dict[Any, Any],
    state: Optional["State"] = None,
    host: Optional["Host"] = None,
    keys_to_check=None,
):
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

    global_kwargs = {}
    found_keys = []

    for key, argument in ALL_ARGUMENTS.items():
        internal_key = _get_internal_key(key)

        if keys_to_check and internal_key not in keys_to_check:
            continue

        handler: Optional[Callable] = None
        default: Optional[Callable] = None

        if isinstance(argument, dict):
            handler = argument.get("handler")
            default = argument.get("default")
            if default:
                default = default(config)

        host_default = getattr(host.data, key, None)

        # TODO: remove this additional check in v3
        if host_default is None and internal_key != key:
            host_default = getattr(host.data, internal_key, None)
            if host_default is not None:
                show_legacy_argument_host_data_warning(internal_key)

        if host_default is not None:
            default = host_default

        if key in kwargs:
            found_keys.append(internal_key)
            value = kwargs.pop(key)

        # TODO: remove this additional check in v3
        elif internal_key in kwargs:
            show_legacy_argument_warning(internal_key, get_call_location(frame_offset=2))
            found_keys.append(internal_key)
            value = kwargs.pop(internal_key)

        else:
            value = meta_kwargs.get(internal_key, default)

        if handler:
            value = handler(config, value)

        global_kwargs[internal_key] = value
    return global_kwargs, found_keys
