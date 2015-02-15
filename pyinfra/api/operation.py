# pyinfra
# File: pyinfra/api/command.py
# Desc: little wrapper to push output from command functions to pyinfra._ops

import pyinfra


def operation(func):
    def inner(*args, **kwargs):
        # Local & globally configurable
        sudo = kwargs.pop('sudo', getattr(pyinfra.config, 'SUDO', False))
        ignore_errors = kwargs.pop('ignore_errors', getattr(pyinfra.config, 'IGNORE_ERRORS', False))
        name = kwargs.pop('name', None)

        # Auto-name the operation
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
            'ignore_errors': ignore_errors
        })

    # Allow the function to be called "inline" within other @op wrapped functions
    inner.inline = func
    return inner
