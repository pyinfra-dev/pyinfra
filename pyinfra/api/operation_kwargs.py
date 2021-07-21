from .util import memoize


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


operation_kwargs = {
    'name': {
        'description': 'Name of the operation.',
    },
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
    'ignore_errors': {
        'description': 'Ignore errors when executing the operation.',
        'default': lambda config: config.IGNORE_ERRORS,
    },
    'success_exit_codes': {
        'description': 'List of exit codes to consider a success.',
        'default': lambda config: [0],
    },
    'timeout': 'Timeout for *each* command executed during the operation.',
    'get_pty': 'Whether to get a pseudoTTY when executing any commands.',
    'stdin': 'String or buffer to send to the stdin of any commands.',
    'precondition': 'Command to execute & check before the operation commands begin.',
    'postcondition': 'Command to execute & check after the operation commands complete.',
}

callback_kwargs = {
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
    'Operation control': operation_kwargs,
    'Callbacks': callback_kwargs,
    'Execution strategy (must be the same for all hosts)': execution_kwargs,
}


def get_execution_kwarg_keys():
    return list(execution_kwargs.keys())


@memoize
def get_executor_kwarg_keys():
    keys = set()
    keys.update(auth_kwargs.keys(), operation_kwargs.keys())
    keys.difference_update({'name', 'ignore_errors', 'precondition', 'postcondition'})
    return list(keys)


def pop_global_op_kwargs(state, host, kwargs):
    '''
    Pop and return operation global keyword arguments, in preferred order:

    + From the current context (operation kwargs)
    + From any current @deploy context (deploy kwargs)
    + From the host data variables
    + From the config variables
    '''

    meta_kwargs = state.deploy_kwargs or {}

    def get_kwarg(key, default=None):
        has_key = key in kwargs
        value = kwargs.pop(key, meta_kwargs.get(key, default))
        return value, has_key

    global_kwargs = {}
    global_kwarg_keys = []

    for _, kwarg_configs in OPERATION_KWARGS.items():
        for key, config in kwarg_configs.items():
            handler = None
            default = None

            if isinstance(config, dict):
                handler = config.get('handler')
                default = config.get('default')
                if default:
                    default = default(state.config)

                host_default = getattr(host.data, key, None)
                if host_default is not None:
                    default = host_default

            value, has_key = get_kwarg(key, default=default)
            if handler:
                value = handler(state.config, value)

            if has_key:
                global_kwarg_keys.append(key)

            global_kwargs[key] = value

    return global_kwargs, global_kwarg_keys
