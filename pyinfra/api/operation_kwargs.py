from pyinfra import logger

from .util import memoize


auth_kwargs = {
    'sudo': {
        'description': 'Execute/apply any changes with sudo.',
        'default': lambda config: config.SUDO,
    },
    'sudo_user': {
        'description': 'Execute/apply any changes with sudo as a non-root user.',
        'default': lambda config: config.SUDO_USER,
    },
    'use_sudo_login': {
        'description': 'Execute ``sudo`` with a login shell.',
        'default': lambda config: config.USE_SUDO_LOGIN,
    },
    'use_sudo_password': {
        'description': 'Whether to use a password with sudo (will ask).',
        'default': lambda config: config.USE_SUDO_PASSWORD,
    },
    'preserve_sudo_env': {
        'description': 'Preserve the shell environment when using sudo.',
        'default': lambda config: config.PRESERVE_SUDO_ENV,
    },
    'su_user': {
        'description': 'Execute/apply any changes with su.',
        'default': lambda config: config.SU_USER,
    },
    'use_su_login': {
        'description': 'Execute ``su`` with a login shell.',
        'default': lambda config: config.USE_SU_LOGIN,
    },
}


def generate_env(config, value):
    env = config.ENV.copy()
    if value:
        env.update(value)
    return env


operation_kwargs = {
    'name': {
        'description': 'Name of the operation',
    },
    'shell_executable': {
        'description': 'The shell to use. Defaults to ``sh`` (Unix) or ``cmd`` (Windows).',
        'default': lambda config: config.SHELL,
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
        'description': 'List of exit codes to consider a success',
        'default': lambda config: [0],
    },
    'timeout': 'Timeout for *each* command executed during the operation.',
    'get_pty': 'Whether to get a pseudoTTY when executing any commands.',
    'stdin': 'String or buffer to send to the stdin of any commands',
}

execution_kwargs = {
    'parallel': 'Run this operation in batches of hosts.',
    'run_once': 'Only execute this operation once, on the first host to see it.',
    'serial': 'Run this operation host by host, rather than in parallel.',
    'precondition': 'Command to execute & check before the operation commands begin.',
    'postcondition': 'Command to execute & check after the operation commands complete.',
}

callback_kwargs = {
    'on_success': 'Callback function to execute on success.',
    'on_error': 'Callback function to execute on error.',
}

OPERATION_KWARGS = {
    'Privilege & user escalation': auth_kwargs,
    'Operation control': operation_kwargs,
    'Operation execution': execution_kwargs,
    'Callbacks': callback_kwargs,
}


@memoize
def get_executor_kwarg_keys():
    keys = set()
    keys.update(auth_kwargs.keys())
    keys.update(operation_kwargs.keys())
    keys.remove('ignore_errors')
    keys.remove('name')
    return list(keys)


@memoize
def show_stdin_global_warning():
    logger.warning('The stdin global argument is in alpha!')


def pop_global_op_kwargs(state, kwargs):
    '''
    Pop and return operation global keyword arguments.
    '''

    meta_kwargs = state.deploy_kwargs or {}

    def get_kwarg(key, default=None):
        return kwargs.pop(key, meta_kwargs.get(key, default))

    global_kwargs = {}

    if 'stdin' in kwargs:
        show_stdin_global_warning()

    for _, kwarg_configs in OPERATION_KWARGS.items():
        for key, config in kwarg_configs.items():
            handler = None
            default = None

            if isinstance(config, dict):
                handler = config.get('handler')
                default = config.get('default')
                if default:
                    default = default(state.config)

            value = get_kwarg(key, default=default)
            if handler:
                value = handler(state.config, value)

            global_kwargs[key] = value

    return global_kwargs
