# pyinfra
# File: pyinfra/api/command.py
# Desc: little wrapper to push output from command functions to pyinfra._commands

import pyinfra


def command(func):
    def inner(*args, **kwargs):
        # Local & globally configurable
        sudo = kwargs.pop('sudo', getattr(pyinfra.config, 'SUDO', False))
        ignore_errors = kwargs.pop('ignore_errors', getattr(pyinfra.config, 'IGNORE_ERRORS', False))

        # Get the commands
        commands = func(*args, **kwargs)
        commands = commands if isinstance(commands, list) else [commands]
        if not commands: return

        pyinfra._meta[pyinfra._current_server]['changes'] += 1
        for command in commands:
            pyinfra._commands[pyinfra._current_server] += [{
                'command': command.strip(),
                'sudo': sudo,
                'ignore_errors': ignore_errors
            }]
            pyinfra._meta[pyinfra._current_server]['commands'] += 1

    return inner
