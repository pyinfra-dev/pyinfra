'''
Operations are the core of pyinfra. The ``@operation`` wrapper intercepts calls
to the function and instead diff against the remote server, outputting commands
to the deploy state. This is then run later by pyinfra's ``__main__`` or the
:doc:`./pyinfra.api.operations` module.
'''

from functools import wraps
from types import FunctionType

import pyinfra

from pyinfra import host, state
from pyinfra import logger
from pyinfra.context import ctx_host, ctx_state

from .arguments import get_execution_kwarg_keys, pop_global_arguments
from .command import StringCommand
from .exceptions import OperationValueError, PyinfraError
from .host import Host
from .util import (
    get_args_kwargs_spec,
    get_call_location,
    get_caller_frameinfo,
    get_operation_order_from_stack,
    make_hash,
    memoize,
)


class OperationMeta(object):
    def __init__(self, hash=None, commands=None):
        # Wrap all the attributes
        commands = commands or []
        self.commands = commands
        self.hash = hash

        # Changed flag = did we do anything?
        self.changed = len(self.commands) > 0

    def __repr__(self):
        '''Return Operation object as a string.'''
        return 'commands:{} changed:{} hash:{}'.format(
            self.commands, self.changed, self.hash)


def add_op(state, op_func, *args, **kwargs):
    '''
    Prepare & add an operation to ``pyinfra.state`` by executing it on all hosts.

    Args:
        state (``pyinfra.api.State`` obj): the deploy state to add the operation
        to op_func (function): the operation function from one of the modules,
        ie ``server.user``
        args/kwargs: passed to the operation function
    '''

    allow_cli_mode = kwargs.pop('_allow_cli_mode', False)
    after_host_callback = kwargs.pop('_after_host_callback', lambda host: None)

    if pyinfra.is_cli and not allow_cli_mode:
        raise PyinfraError((
            '`add_op` should not be called when pyinfra is executing in CLI mode! ({0})'
        ).format(get_call_location()))

    # This ensures that every time an operation is added (API mode), it is simply
    # appended to the operation order.
    kwargs['_op_order_number'] = len(state.op_meta)

    hosts = kwargs.pop('host', state.inventory.iter_active_hosts())
    if isinstance(hosts, Host):
        hosts = [hosts]

    with ctx_state.use(state):
        results = {}
        for op_host in hosts:
            with ctx_host.use(op_host):
                results[op_host] = op_func(*args, **kwargs)
            after_host_callback(op_host)

    return results


@memoize
def show_state_host_arguments_warning(call_location):
    logger.warning((
        '{0}:\n\tLegacy operation function detected! Operations should no longer define '
        '`state` and `host` arguments.'
    ).format(call_location))


def operation(func=None, pipeline_facts=None, is_idempotent=True, frame_offset=1):
    '''
    Decorator that takes a simple module function and turn it into the internal
    operation representation that consists of a list of commands + options
    (sudo, (sudo|su)_user, env).
    '''

    # If not decorating, return function with config attached
    if func is None:
        def decorator(f):
            f.pipeline_facts = pipeline_facts
            f.is_idempotent = is_idempotent
            return operation(f, frame_offset=2)
        return decorator

    # Check whether an operation is "legacy" - ie contains state=None, host=None kwargs
    # TODO: remove this in v3
    is_legacy = False
    args, kwargs = get_args_kwargs_spec(func)
    if all(key in kwargs and kwargs[key] is None for key in ('state', 'host')):
        show_state_host_arguments_warning(get_call_location(frame_offset=frame_offset))
        is_legacy = True
    func.is_legacy = is_legacy

    # Actually decorate!
    @wraps(func)
    def decorated_func(*args, **kwargs):
        # Configure operation
        #

        # Get the meta kwargs (globals that apply to all hosts)
        global_kwargs, global_kwarg_keys = pop_global_arguments(state, host, kwargs)

        # If this op is being called inside another, just return here
        # (any unwanted/op-related kwargs removed above).
        if host.in_op:
            if global_kwarg_keys:
                raise PyinfraError((
                    'Nested operation called with global arguments: {0} ({1})'
                ).format(global_kwarg_keys, get_call_location()))
            return func(*args, **kwargs) or []

        # If this is a legacy operation function (ie - state & host arg kwargs), ensure that state
        # and host are included as kwargs.
        if func.is_legacy:
            if 'state' not in kwargs:
                kwargs['state'] = state
            if 'host' not in kwargs:
                kwargs['host'] = host
        # If not legacy, pop off any state/host kwargs that may come from legacy @deploy functions
        else:
            kwargs.pop('state', None)
            kwargs.pop('host', None)

        # Name the operation
        name = global_kwargs.get('name')
        add_args = False

        if name:
            names = {name}

        # Generate an operation name if needed (Module/Operation format)
        else:
            add_args = True

            if func.__module__:
                module_bits = func.__module__.split('.')
                module_name = module_bits[-1]
                name = '{0}/{1}'.format(module_name.title(), func.__name__.title())
            else:
                name = func.__name__

            names = {name}

        if host.current_deploy_name:
            names = {
                '{0} | {1}'.format(host.current_deploy_name, name)
                for name in names
            }

        # API mode: `add_op` provides the order number
        op_order_number = kwargs.pop('_op_order_number', None)
        if op_order_number is not None:
            op_order = [op_order_number]

        # CLI mode: we simply use the line order to place the operation - ie starting
        # with the current operation call we traverse up the stack to the first occurrence
        # of the current deploy file. This means operations are ordered as you would expect
        # reading the deployment code, even though the code is technically executed once
        # for each host sequentially.
        elif pyinfra.is_cli:
            op_order = get_operation_order_from_stack(state)

        # API mode: no op order number, deploy provided or fail
        else:
            # API mode deployments are a special case - the order is based on where the
            # deploy function is called first, and then the operation position *within*
            # that function. Because functions have to exist in one file, we can simply
            # use the line number to get correct ordering.
            if host.in_deploy:
                frameinfo = get_caller_frameinfo()
                op_order = host.current_deploy_op_order + [frameinfo.lineno]
            else:
                raise PyinfraError((
                    'Operation order number not provided in API mode - '
                    'you must use `add_op` to add operations.'
                ))

        # Make a hash from the call stack lines
        op_hash = make_hash(op_order)

        # Avoid adding duplicates! This happens if an operation is called within
        # a loop - such that the filename/lineno/code _are_ the same, but the
        # arguments might be different. We just append an increasing number to
        # the op hash and also handle below with the op order.
        host_op_hashes = state.meta[host]['op_hashes']
        duplicate_op_count = 0
        while op_hash in host_op_hashes:
            logger.debug('Duplicate hash ({0}) detected!'.format(op_hash))
            op_hash = '{0}-{1}'.format(op_hash, duplicate_op_count)
            duplicate_op_count += 1

        host_op_hashes.add(op_hash)

        if duplicate_op_count:
            op_order.append(duplicate_op_count)

        op_order = tuple(op_order)

        logger.debug('Adding operation, {0}, opOrder={1}, opHash={2}'.format(
            names, op_order, op_hash,
        ))
        state.op_line_numbers_to_hash[op_order] = op_hash

        # Ensure shared (between servers) operation meta
        op_meta = state.op_meta.setdefault(op_hash, {
            'names': set(),
            'args': [],
        })

        for key in get_execution_kwarg_keys():
            global_value = global_kwargs.pop(key)
            op_meta_value = op_meta.get(key)

            if op_meta_value and global_value != op_meta_value:
                raise OperationValueError('Cannot have different values for `{0}`.'.format(key))

            op_meta[key] = global_value

        # Add any new names to the set
        op_meta['names'].update(names)

        # Attach normal args, if we're auto-naming this operation
        if add_args:
            for arg in args:
                if isinstance(arg, FunctionType):
                    arg = arg.__name__

                if arg not in op_meta['args']:
                    op_meta['args'].append(arg)

            # Attach keyword args
            for key, value in kwargs.items():
                if isinstance(value, FunctionType):
                    value = value.__name__

                arg = '='.join((str(key), str(value)))
                if arg not in op_meta['args']:
                    op_meta['args'].append(arg)

        # Check if we're actually running the operation on this host
        #

        # Run once and we've already added meta for this op? Stop here.
        if op_meta['run_once']:
            has_run = False
            for ops in state.ops.values():
                if op_hash in ops:
                    has_run = True
                    break

            if has_run:
                return OperationMeta(op_hash)

        # "Run" operation
        #

        # Otherwise, flag as in-op and run it to get the commands
        host.in_op = True
        host.current_op_hash = op_hash
        host.current_op_global_kwargs = global_kwargs

        # Convert to list as the result may be a generator
        commands = func(*args, **kwargs)
        commands = [  # convert any strings -> StringCommand's
            StringCommand(command.strip())
            if isinstance(command, str) else command
            for command in commands
        ]

        host.in_op = False
        host.current_op_hash = None
        host.current_op_global_kwargs = None

        # Add host-specific operation data to state
        #

        # We're doing some commands, meta/ops++
        state.meta[host]['ops'] += 1
        state.meta[host]['commands'] += len(commands)

        # Add the server-relevant commands
        state.ops[host][op_hash] = {
            'commands': commands,
            'global_kwargs': global_kwargs,
        }

        # Return result meta for use in deploy scripts
        return OperationMeta(op_hash, commands)

    decorated_func._pyinfra_op = func
    return decorated_func
