auth_kwargs = {
    'sudo': {
        'description': 'Execute/apply any changes with sudo.',
        'default': lambda state: state.config.SUDO,
    },
    'sudo_user': {
        'description': 'Execute/apply any changes with sudo as a non-root user.',
        'default': lambda state: state.config.SUDO_USER,
    },
    'su_user': {
        'description': 'Execute/apply any changes with su.',
        'default': lambda state: state.config.SU_USER,
    },
    'preserve_sudo_env': {
        'description': 'Preserve the shell environment when using sudo.',
        'default': lambda state: state.config.PRESERVE_SUDO_ENV,
    },
}


def generate_env(state, value):
    env = state.config.ENV.copy()
    if value:
        env.update(value)
    return env


operation_kwargs = {
    'shell_executable': {
        'description': 'The shell executable to use',
        'default': lambda state: state.config.SHELL,
    },
    'env': {
        'description': 'Dictionary of environment variables to set.',
        'handler': generate_env,
    },
    'ignore_errors': {
        'description': 'Ignore errors when executing the operation.',
        'default': lambda state: state.config.IGNORE_ERRORS,
    },
    'timeout': 'Timeout for *each* command executed during the operation.',
    'get_pty': 'Whether to get a pseudoTTY when executing any commands.',
}

execution_kwargs = {
    'parallel': 'Run this operation in batches of hosts.',
    'run_once': 'Only execute this operation once, on the first host to see it.',
    'serial': 'Run this operation host by host, rather than in parallel.',
}

callback_kwargs = {
    'on_success': 'Callback function to execute on success.',
    'on_error': 'Callback function to execute on error.',
}

hidden_commands = {
    'op': {},
}

OPERATION_KWARGS = {
    'Privilege & user escalation': auth_kwargs,
    'Operation control': operation_kwargs,
    'Operation execution': execution_kwargs,
    'Callbacks': callback_kwargs,
    None: hidden_commands,
}
