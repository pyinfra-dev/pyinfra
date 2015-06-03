# pyinfra
# File: pyinfra/api/operation.py
# Desc: wraps deploy script operations and puts commands -> pyinfra._ops

'''
Operations are the core of pyinfra. These wrappers mean that when you call an operation
in a deploy script, what actually happens is we diff the remote server and build a list
of commands to alter the diff to the specified arguments. This is then saved to be run
later by pyinfra's __main__.
'''

from functools import wraps
from copy import deepcopy

import pyinfra


def make_hash(obj):
    '''
    Make a hash from an arbitrary nested dictionary, list, tuple or set, used
    to generate ID's for operations based on their name & arguments.
    '''
    if type(obj) in (set, tuple, list):
        return hash(tuple([make_hash(e) for e in obj]))

    elif not isinstance(obj, dict):
        return hash(obj)

    new_obj = deepcopy(obj)
    for k, v in new_obj.items():
        new_obj[k] = make_hash(v)

    return hash(tuple(set(new_obj.items())))


def operation(func):
    '''
    Takes a simple module function and turn it into the internal operation representation
    consists of a list of commands + options (sudo, user, env).
    '''
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Locally & globally configurable
        sudo = kwargs.pop('sudo', getattr(pyinfra.config, 'SUDO', False))
        sudo_user = kwargs.pop('sudo_user', getattr(pyinfra.config, 'SUDO_USER', None))
        ignore_errors = kwargs.pop('ignore_errors', getattr(pyinfra.config, 'IGNORE_ERRORS', False))

        # Forces serial mode for this operation (--serial for one op)
        serial = kwargs.pop('serial', False)
        # Only runs this operation once
        run_once = kwargs.pop('run_once', False)

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
            name = '{}/{}'.format(module_name.title(), func.__name__.title())

        # Get/generate a hash for this op
        op_hash = kwargs.pop('op', None)
        if op_hash is None:
            op_hash = (name, sudo, sudo_user, ignore_errors, env, args, kwargs)

        op_hash = make_hash(op_hash)

        # If this op is being called inside another, just return here
        # (any unwanted/op-related kwargs removed above)
        if pyinfra._in_op:
            return func(*args, **kwargs)

        # Otherwise, flag as in-op and run it to get the commands
        pyinfra._in_op = True
        commands = func(*args, **kwargs)
        pyinfra._in_op = False

        # No commands, no op
        if not isinstance(commands, list):
            return

        # Add the hash to the operational order if not already in there
        if op_hash not in pyinfra._op_order:
            pyinfra._op_order.append(op_hash)

        # We're doing some commands, meta/ops++
        pyinfra._meta[pyinfra._current_server]['ops'] += 1
        pyinfra._meta[pyinfra._current_server]['commands'] += len(commands)

        # Add the server-relevant commands/env to the current server
        pyinfra._ops[pyinfra._current_server][op_hash] = {
            'commands': commands,
            'env': env
        }

        # Create/update shared (between servers) operation meta
        op_meta = pyinfra._op_meta.setdefault(op_hash, {
            'names': [],
            'sudo': sudo,
            'sudo_user': sudo_user,
            'ignore_errors': ignore_errors,
            'serial': serial,
            'run_once': run_once
        })
        if name not in op_meta['names']:
            op_meta['names'].append(name)

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
