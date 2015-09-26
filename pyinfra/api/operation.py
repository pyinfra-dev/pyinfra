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
from types import FunctionType

from pyinfra import host, state

from .util import make_hash
from .attrs import AttrBase


def add_op(op_func, *args, **kwargs):
    '''Prepare & add an operation to pyinfra.state by executing it on all hosts.'''
    for host_obj in state.inventory:
        host.set(host_obj)
        op_func(*args, **kwargs)


def operation_facts(*facts, **arg_facts):
    '''
    Allows a module to specify the facts an operation will use. This is used in CLI mode
    to optimise performance by pre-gathering these facts in parallel.
    '''
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            return func(*args, **kwargs)

        decorated_function.facts = facts
        return decorated_function
    return decorator


def operation(func):
    '''
    Takes a simple module function and turn it into the internal operation representation
    consists of a list of commands + options (sudo, user, env).
    '''
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Locally & globally configurable
        sudo = kwargs.pop('sudo', state.config.SUDO)
        sudo_user = kwargs.pop('sudo_user', state.config.SUDO_USER)
        ignore_errors = kwargs.pop('ignore_errors', state.config.IGNORE_ERRORS)

        # If we're in pre_run mode, we only need to pull out any .facts on this function
        # (as set by the operation_facts decorator above) and attach to the state, ready
        # to be pre-fetched.
        if state.pre_run:
            facts = getattr(func, 'facts', [])
            if facts:
                state.pre_run_facts.extend(
                    (fact, sudo, sudo_user)
                    for fact in facts
                )
            return

        # Forces serial mode for this operation (--serial for one op)
        serial = kwargs.pop('serial', False)
        # Only runs this operation once
        run_once = kwargs.pop('run_once', False)
        # Timeout on running the command
        timeout = kwargs.pop('timeout', None)

        # Config env followed by command-level env
        env = state.config.ENV
        env.update(kwargs.pop('env', {}))

        # Name the operation
        name = kwargs.pop('name', None)
        if name is None:
            module_bits = func.__module__.split('.')
            module_name = module_bits[-1]
            name = '{}/{}'.format(module_name.title(), func.__name__.title())

        # Get/generate a hash for this op
        op_hash = kwargs.pop('op', None)

        # If this op is being called inside another, just return here
        # (any unwanted/op-related kwargs removed above)
        if state.in_op:
            return func(*args, **kwargs) or []

        if op_hash is None:
            # Convert any AttrBase items (returned by host.data) arg
            # this means if one of the args is host.data.app_dir which is set to different
            # values on different hosts it will still generate one operation.
            hash_args = [
                arg.pyinfra_attr_key if isinstance(arg, AttrBase) else
                arg.__name__ if isinstance(arg, FunctionType) else arg
                for arg in args
            ]

            hash_kwargs = {
                key: arg.pyinfra_attr_key if isinstance(arg, AttrBase) else
                arg.__name__ if isinstance(arg, FunctionType) else arg
                for key, arg in kwargs.iteritems()
            }

            op_hash = (name, sudo, sudo_user, ignore_errors, env, hash_args, hash_kwargs)

        op_hash = make_hash(op_hash)

        # Otherwise, flag as in-op and run it to get the commands
        state.in_op = True
        state.current_op_sudo = (sudo, sudo_user)
        commands = func(*args, **kwargs)
        state.in_op = False
        state.current_op_sudo = None

        # No commands, no changes
        if not isinstance(commands, list):
            commands = []

        # Add the hash to the operational order if not already in there
        # we insert the hash at the current position for the current host, such that
        # deploy scripts run in the order they are defined *for each host*. Using if
        # statements without matching the operations within (by op_name and the number of
        # them) will results in them not running in the order defined in the deploy script,
        # but they will remain in-order per-host.
        if op_hash not in state.op_order:
            current_ops = state.meta[host.ssh_hostname]['ops']
            state.op_order.insert(current_ops, op_hash)

        # We're doing some commands, meta/ops++
        state.meta[host.ssh_hostname]['ops'] += 1
        state.meta[host.ssh_hostname]['commands'] += len(commands)

        # Add the server-relevant commands/env to the current server
        state.ops[host.ssh_hostname][op_hash] = {
            'commands': commands,
            'env': env
        }

        # Create/update shared (between servers) operation meta
        op_meta = state.op_meta.setdefault(op_hash, {
            'names': [],
            'sudo': sudo,
            'sudo_user': sudo_user,
            'ignore_errors': ignore_errors,
            'serial': serial,
            'run_once': run_once,
            'timeout': timeout
        })
        if name not in op_meta['names']:
            op_meta['names'].append(name)

    # Add __decorated__ for pydocs
    decorated_function.__decorated__ = getattr(func, '__decorated__', func)

    return decorated_function
