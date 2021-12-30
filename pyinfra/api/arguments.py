from pyinfra import logger

from .util import get_call_location, memoize


auth_kwargs = {
    'sudo': {
        'description': 'Execute/apply any changes with ``sudo``.',
        'default': lambda config: config.SUDO,
    },
    'sudo_user': {
        'description': 'Execute/apply any changes with ``sudo`` as a non-root user.',
        'default': lambda config: config.SUDO_USER,
    },
    'use_sudo_login': {
        'description': 'Execute ``sudo`` with a login shell.',
        'default': lambda config: config.USE_SUDO_LOGIN,
    },
    'use_sudo_password': {
        'description': 'Whether to use a password with ``sudo`` (will ask).',
        'default': lambda config: config.USE_SUDO_PASSWORD,
    },
    'preserve_sudo_env': {
        'description': 'Preserve the shell environment when using ``sudo``.',
        'default': lambda config: config.PRESERVE_SUDO_ENV,
    },
    'su_user': {
        'description': 'Execute/apply any changes with ``su``.',
        'default': lambda config: config.SU_USER,
    },
    'use_su_login': {
        'description': 'Execute ``su`` with a login shell.',
        'default': lambda config: config.USE_SU_LOGIN,
    },
    'preserve_su_env': {
        'description': 'Preserve the shell environment when using ``su``.',
        'default': lambda config: config.PRESERVE_SU_ENV,
    },
    'su_shell': {
        'description': (
            'Use this shell (instead of user login shell) when using ``su``). '
            'Only available under Linux, for use when using `su` with a user that '
            'has nologin/similar as their login shell.'
        ),
        'default': lambda config: config.SU_SHELL,
    },
    'doas': {
        'description': 'Execute/apply any changes with ``doas``.',
        'defailt': lambda config: config.DOAS,
    },
    'doas_user': {
        'description': 'Execute/apply any changes with ``doas`` as a non-root user.',
        'default': lambda config: config.DOAS_USER,
    },
}


def generate_env(config, value):
    env = config.ENV.copy()
    if value:
        env.update(value)
    return env


shell_kwargs = {
    'shell_executable': {
        'description': 'The shell to use. Defaults to ``sh`` (Unix) or ``cmd`` (Windows).',
        'default': lambda config: config.SHELL,
    },
    'chdir': {
        'description': 'Directory to switch to before executing the command.',
    },
    'env': {
        'description': 'Dictionary of environment variables to set.',
        'handler': generate_env,
    },
    'success_exit_codes': {
        'description': 'List of exit codes to consider a success.',
        'default': lambda config: [0],
    },
    'timeout': 'Timeout for *each* command executed during the operation.',
    'get_pty': 'Whether to get a pseudoTTY when executing any commands.',
    'stdin': 'String or buffer to send to the stdin of any commands.',
}

meta_kwargs = {
    'name': {
        'description': 'Name of the operation.',
    },
    'ignore_errors': {
        'description': 'Ignore errors when executing the operation.',
        'default': lambda config: config.IGNORE_ERRORS,
    },
    'precondition': 'Command to execute & check before the operation commands begin.',
    'postcondition': 'Command to execute & check after the operation commands complete.',
    'on_success': 'Callback function to execute on success.',
    'on_error': 'Callback function to execute on error.',
}

# Execution kwargs are global - ie must be identical for every host
execution_kwargs = {
    'parallel': {
        'description': 'Run this operation in batches of hosts.',
        'default': lambda config: config.PARALLEL,
    },
    'run_once': {
        'description': 'Only execute this operation once, on the first host to see it.',
        'default': lambda config: False,
    },
    'serial': {
        'description': 'Run this operation host by host, rather than in parallel.',
        'default': lambda config: False,
    },
}

OPERATION_KWARGS = {
    'Privilege & user escalation': auth_kwargs,
    'Shell control & features': shell_kwargs,
    'Operation meta & callbacks': meta_kwargs,
    'Execution strategy (must be the same for all hosts)': execution_kwargs,
}


def get_execution_kwarg_keys():
    return list(execution_kwargs.keys())


@memoize
def get_executor_kwarg_keys():
    keys = set()
    keys.update(auth_kwargs.keys(), shell_kwargs.keys())
    return list(keys)


@memoize
def show_legacy_global_argument_warning(key, call_location):
    logger.warning((
        '{0}:\n\tGlobal arguments should be prefixed "_", '
        'please us the `{1}` keyword argument in place of `{2}`.'
    ).format(call_location, '_{0}'.format(key), key))


def pop_global_op_kwargs(state, host, kwargs):
    '''
    Pop and return operation global keyword arguments, in preferred order:

    + From the current context (a direct @operator or @deploy function being called)
    + From any current @deploy context (deploy kwargs)
    + From the host data variables
    + From the config variables

    Note this function is only called directly in the @operation & @deploy decorator
    wrappers which the user should pass global arguments prefixed "_".
    '''

    meta_kwargs = state.deploy_kwargs or {}

    global_kwargs = {}
    found_keys = []

    for _, kwarg_configs in OPERATION_KWARGS.items():
        for key, config in kwarg_configs.items():
            handler = None
            default = None

            if isinstance(config, dict):
                handler = config.get('handler')
                default = config.get('default')
                if default:
                    default = default(state.config)

            # TODO: why is 'name' hard-coded as the only non-_-prefixed key
            direct_key = '_{0}'.format(key) if key != 'name' else key

            # TODO: do we support global arguments in host data w/ or w/o the _ prefix? Or both?
            host_default = getattr(host.data, direct_key, None) or getattr(host.data, key, None)
            if host_default is not None:
                default = host_default

            if direct_key in kwargs:
                found_keys.append(key)
                value = kwargs.pop(direct_key)

            # COMPAT w/<v3
            # TODO: remove this additional check
            elif key in kwargs:
                show_legacy_global_argument_warning(key, get_call_location(frame_offset=2))
                found_keys.append(key)
                value = kwargs.pop(key)

            else:
                value = meta_kwargs.get(key, default)

            if handler:
                value = handler(state.config, value)

            global_kwargs[key] = value
    return global_kwargs, found_keys
