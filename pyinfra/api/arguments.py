from pyinfra import context, logger

from .util import get_call_location, memoize

auth_kwargs = {
    "_sudo": {
        "description": "Execute/apply any changes with ``sudo``.",
        "default": lambda config: config.SUDO,
    },
    "_sudo_user": {
        "description": "Execute/apply any changes with ``sudo`` as a non-root user.",
        "default": lambda config: config.SUDO_USER,
    },
    "_use_sudo_login": {
        "description": "Execute ``sudo`` with a login shell.",
        "default": lambda config: config.USE_SUDO_LOGIN,
    },
    "_use_sudo_password": {
        "description": "Whether to use a password with ``sudo`` (will ask).",
        "default": lambda config: config.USE_SUDO_PASSWORD,
    },
    "_preserve_sudo_env": {
        "description": "Preserve the shell environment when using ``sudo``.",
        "default": lambda config: config.PRESERVE_SUDO_ENV,
    },
    "_su_user": {
        "description": "Execute/apply any changes with ``su``.",
        "default": lambda config: config.SU_USER,
    },
    "_use_su_login": {
        "description": "Execute ``su`` with a login shell.",
        "default": lambda config: config.USE_SU_LOGIN,
    },
    "_preserve_su_env": {
        "description": "Preserve the shell environment when using ``su``.",
        "default": lambda config: config.PRESERVE_SU_ENV,
    },
    "_su_shell": {
        "description": (
            "Use this shell (instead of user login shell) when using ``su``). "
            "Only available under Linux, for use when using `su` with a user that "
            "has nologin/similar as their login shell."
        ),
        "default": lambda config: config.SU_SHELL,
    },
    "_doas": {
        "description": "Execute/apply any changes with ``doas``.",
        "defailt": lambda config: config.DOAS,
    },
    "_doas_user": {
        "description": "Execute/apply any changes with ``doas`` as a non-root user.",
        "default": lambda config: config.DOAS_USER,
    },
}


def generate_env(config, value):
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
    },
    "_chdir": {
        "description": "Directory to switch to before executing the command.",
    },
    "_env": {
        "description": "Dictionary of environment variables to set.",
        "handler": generate_env,
    },
    "_success_exit_codes": {
        "description": "List of exit codes to consider a success.",
        "default": lambda config: [0],
    },
    "_timeout": "Timeout for *each* command executed during the operation.",
    "_get_pty": "Whether to get a pseudoTTY when executing any commands.",
    "_stdin": "String or buffer to send to the stdin of any commands.",
}

meta_kwargs = {
    # NOTE: name is the only non-_-prefixed argument
    "name": {
        "description": "Name of the operation.",
    },
    "_ignore_errors": {
        "description": "Ignore errors when executing the operation.",
        "default": lambda config: config.IGNORE_ERRORS,
    },
    "_precondition": "Command to execute & check before the operation commands begin.",
    "_postcondition": "Command to execute & check after the operation commands complete.",
    "_on_success": "Callback function to execute on success.",
    "_on_error": "Callback function to execute on error.",
}

# Execution kwargs are global - ie must be identical for every host
execution_kwargs = {
    "_parallel": {
        "description": "Run this operation in batches of hosts.",
        "default": lambda config: config.PARALLEL,
    },
    "_run_once": {
        "description": "Only execute this operation once, on the first host to see it.",
        "default": lambda config: False,
    },
    "_serial": {
        "description": "Run this operation host by host, rather than in parallel.",
        "default": lambda config: False,
    },
}

OPERATION_KWARGS = {
    "Privilege & user escalation": auth_kwargs,
    "Shell control & features": shell_kwargs,
    "Operation meta & callbacks (not available in facts)": meta_kwargs,
    "Execution strategy (not available in facts, must be the same for all hosts)": execution_kwargs,
}


def _get_internal_key(key):
    if key.startswith("_"):
        return key[1:]
    return key


@memoize
def get_execution_kwarg_keys():
    return [_get_internal_key(key) for key in execution_kwargs.keys()]


@memoize
def get_executor_kwarg_keys():
    keys = set()
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


def pop_global_arguments(kwargs, state=None, host=None, keys_to_check=None):
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

    TODO: is this wird-ness acceptable? Is it worth updating internal use to _prefix?
    """

    state = state or context.state
    host = host or context.host

    config = state.config
    if context.ctx_config.isset():
        config = context.config

    meta_kwargs = host.current_deploy_kwargs or {}

    global_kwargs = {}
    found_keys = []

    for _, arguments in OPERATION_KWARGS.items():
        for key, argument in arguments.items():
            internal_key = _get_internal_key(key)

            if keys_to_check and internal_key not in keys_to_check:
                continue

            handler = None
            default = None

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
