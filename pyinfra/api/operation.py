# pyinfra
# File: pyinfra/api/operation.py
# Desc: wraps deploy script operations and puts commands -> pyinfra._ops

'''
Operations are the core of pyinfra. The ``@operation`` wrapper intercepts calls to the
function and instead diff against the remote server, outputting commands to the deploy
state. This is then run later by pyinfra's ``__main__`` or the :doc:`./operations`.
'''

from functools import wraps

from pyinfra import pseudo_state, pseudo_host
from pyinfra.pseudo_modules import PseudoModule
from pyinfra.api.exceptions import PyinfraError

from .host import Host
from .state import State
from .util import make_hash, get_arg_name


class OperationMeta(object):
    def __init__(self, hash=None, commands=None):
        self.hash = hash
        self.commands = commands or []

        # Changed flag = did we do anything?
        self.changed = len(self.commands) > 0


def add_op(state, op_func, *args, **kwargs):
    '''
    Prepare & add an operation to pyinfra.state by executing it on all hosts.

    Args:
        state (``pyinfra.api.State`` obj): the deploy state to add the operation to
        op_func (function): the operation function from one of the modules, ie \
            ``server.user``
        args/kwargs: passed to the operation function
    '''

    for host in state.inventory:
        op_func(state, host, *args, **kwargs)


def operation(func):
    '''
    Decorator that takes a simple module function and turn it into the internal operation
    representation that consists of a list of commands + options (sudo, user, env).
    '''

    @wraps(func)
    def decorated_function(*args, **kwargs):
        # If we're in CLI mode, there's no state/host passed down, we need to use the
        # global "pseudo" modules.
        if len(args) < 2 or not (
            isinstance(args[0], (State, PseudoModule))
            and isinstance(args[1], (Host, PseudoModule))
        ):
            state = pseudo_state
            host = pseudo_host
            if not state.active:
                return OperationMeta()

        # Otherwise (API mode) we just trim off the commands
        else:
            args_copy = list(args)
            state, host = args[0], args[1]
            args = args_copy[2:]

        # Locally & globally configurable
        sudo = kwargs.pop('sudo', state.config.SUDO)
        sudo_user = kwargs.pop('sudo_user', state.config.SUDO_USER)
        ignore_errors = kwargs.pop('ignore_errors', state.config.IGNORE_ERRORS)

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
            return func(state, host, *args, **kwargs) or []

        # Convert any AttrBase items (returned by host.data), see attrs.py.
        if op_hash is None:
            hash_args = [
                get_arg_name(arg)
                for arg in args
            ]

            hash_kwargs = {
                key: get_arg_name(arg)
                for key, arg in kwargs.iteritems()
            }

            op_hash = (name, sudo, sudo_user, ignore_errors, env, hash_args, hash_kwargs)

        op_hash = make_hash(op_hash)

        # Otherwise, flag as in-op and run it to get the commands
        state.in_op = True
        state.current_op_sudo = (sudo, sudo_user)

        try:
            commands = func(state, host, *args, **kwargs)
        except Exception as e:
            raise PyinfraError('Operation error with {0}: {1}'.format(host.name, e))

        state.in_op = False
        state.current_op_sudo = None

        # Add the hash to the operational order if not already in there. To ensure that
        # deploys run as defined in the deploy file *per host* we keep track of each hosts
        # latest op hash, and use that to insert new ones. Note that using the op kwarg
        # on operations can break the ordering when imbalanced (between if statements in
        # deploy file, for example).
        if op_hash not in state.op_order:
            previous_op_hash = state.meta[host.name]['latest_op_hash']

            if previous_op_hash:
                index = state.op_order.index(previous_op_hash)
            else:
                index = 0

            state.op_order.insert(index + 1, op_hash)

        # We're doing some commands, meta/ops++
        state.meta[host.name]['ops'] += 1
        state.meta[host.name]['commands'] += len(commands)
        state.meta[host.name]['latest_op_hash'] = op_hash

        # Add the server-relevant commands/env to the current server
        state.ops[host.name][op_hash] = {
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

        # Return result meta for use in deploy scripts
        return OperationMeta(op_hash, commands)

    decorated_function._pyinfra_op = func
    return decorated_function
