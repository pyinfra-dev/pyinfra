# pyinfra
# File: pyinfra/api/command.py
# Desc: little wrapper to push output from command functions to pyinfra._ops

from functools import wraps

import pyinfra


def operation(func):
    '''
    Takes a simple module function and turn it into the internal operation representation
    consists of a list of commands + options (sudo, user, env)
    '''
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Locally & globally configurable
        sudo = kwargs.pop('sudo', getattr(pyinfra.config, 'SUDO', False))
        sudo_user = kwargs.pop('sudo_user', getattr(pyinfra.config, 'SUDO_USER', None))
        ignore_errors = kwargs.pop('ignore_errors', getattr(pyinfra.config, 'IGNORE_ERRORS', False))

        # Operations can have "base_envs" via the operation_env decorator
        # then we extend by config.ENV, and finally kwargs['env']
        env = getattr(func, 'env', {})
        env.update(getattr(pyinfra.config, 'ENV', {}))
        env.update(kwargs.pop('env', {}))

        # Name the operation
        name = kwargs.pop('name', None)
        if name is None:
            module_bits = func.__module__.split('.')
            module_name = module_bits[-1]
            name = '{} / {}'.format(module_name.title(), func.__name__.title())

        # Get the commands
        commands = func(*args, **kwargs)
        if not isinstance(commands, list):
            return

        # We're doing some commands, ops++
        pyinfra._meta[pyinfra._current_server]['ops'] += 1

        # Fixup the commands, & to meta
        commands = [command.strip() for command in commands]
        pyinfra._meta[pyinfra._current_server]['commands'] += len(commands)

        # Add the operation
        pyinfra._ops[pyinfra._current_server].append({
            'name': name,
            'commands': commands,
            'sudo': sudo,
            'sudo_user': sudo_user,
            'env': env,
            'ignore_errors': ignore_errors
        })

    # Allow the function to be called "inline" within other @op wrapped functions
    decorated_function.inline = func
    return decorated_function


def operation_env(**kwargs):
    '''Pre-wraps an operation with kwarg environment variables'''
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            return func(*args, **kwargs)

        decorated_function.env = kwargs
        return decorated_function
    return decorator
