'''
Operations are the core of pyinfra. The ``@operation`` wrapper intercepts calls
to the function and instead diff against the remote server, outputting commands
to the deploy state. This is then run later by pyinfra's ``__main__`` or the
:doc:`./pyinfra.api.operations` module.
'''

from __future__ import unicode_literals

from functools import wraps
from types import FunctionType

import six

import pyinfra

from pyinfra import logger, pseudo_host, pseudo_state

from .command import StringCommand
from .exceptions import OperationValueError, PyinfraError
from .host import Host
from .operation_kwargs import get_execution_kwarg_keys, pop_global_op_kwargs
from .state import State
from .util import (
    get_arg_value,
    get_call_location,
    get_caller_frameinfo,
    get_operation_order_from_stack,
    make_hash,
    memoize,
    unroll_generators,
)


# List of available operation names
OPERATIONS = []


def get_operation_names():
    '''
    Returns a list of available operations.
    '''

    return OPERATIONS


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

    kwargs['state'] = state

    hosts = kwargs.pop('host', state.inventory.iter_active_hosts())
    if isinstance(hosts, Host):
        hosts = [hosts]

    results = {}
    for host in hosts:
        kwargs['host'] = host
        results[host] = op_func(*args, **kwargs)
        after_host_callback(host)

    return results


@memoize
def show_set_name_warning(call_location):
    logger.warning((
        '{0}:\n\tUse of a `set` to name operations is deprecated, '
        'please us the `name` keyword argument.'
    ).format(call_location))


@memoize
def show_state_host_arguments_warning(call_location):
    logger.warning((
        '{0}:\n\tPassing `state` and `host` as the first two arguments to operations is '
        'deprecated, please use `state` and `host` keyword arguments.'
    ).format(call_location))


def operation(func=None, pipeline_facts=None, is_idempotent=True):
    '''
    Decorator that takes a simple module function and turn it into the internal
    operation representation that consists of a list of commands + options
    (sudo, (sudo|su)_user, env).
    '''

    # If not decorating, return function with config attached
    if func is None:
        def decorator(f):
            setattr(f, 'pipeline_facts', pipeline_facts)
            setattr(f, 'is_idempotent', is_idempotent)
            return operation(f)
        return decorator

    # Index the operation!
    # TODO: remove this in v2
    if func.__module__:
        module_bits = func.__module__.split('.')
        module_name = module_bits[-1]
        op_name = '.'.join((module_name, func.__name__))
        OPERATIONS.append(op_name)

    # Actually decorate!
    @wraps(func)
    def decorated_func(*args, **kwargs):
        # Prepare state/host
        #

        # State & host passed in as kwargs (API, nested op, @deploy op)
        if 'state' in kwargs and 'host' in kwargs:
            state = kwargs['state']
            host = kwargs['host']

        # State & host passed in as first two arguments (LEGACY)
        elif len(args) >= 2 and isinstance(args[0], State) and isinstance(args[1], Host):
            show_state_host_arguments_warning(get_call_location())
            state = kwargs['state'] = args[0]
            host = kwargs['host'] = args[1]
            args_copy = list(args)
            args = args_copy[2:]

        # Finally, still no state+host? Use pseudo if we're CLI mode, or fail
        elif pyinfra.is_cli:
            state = kwargs['state'] = pseudo_state._module
            host = kwargs['host'] = pseudo_host._module

            if state.in_op:
                raise PyinfraError((
                    'Nested operation called without state/host: {0} ({1})'
                ).format(op_name, get_call_location()))

            if state.in_deploy:
                raise PyinfraError((
                    'Nested deploy operation called without state/host: {0} ({1})'
                ).format(op_name, get_call_location()))

        else:
            raise PyinfraError((
                'API operation called without state/host: {0} ({1})'
            ).format(op_name, get_call_location()))

        # Configure operation
        #

        # Get the meta kwargs (globals that apply to all hosts)
        global_kwargs, global_kwarg_keys = pop_global_op_kwargs(state, host, kwargs)

        # If this op is being called inside another, just return here
        # (any unwanted/op-related kwargs removed above).
        if state.in_op:
            if global_kwarg_keys:
                raise PyinfraError((
                    'Nested operation called with global arguments: {0} ({1})'
                ).format(global_kwarg_keys, get_call_location()))
            return func(*args, **kwargs) or []

        # Name the operation
        name = global_kwargs.get('name')
        add_args = False

        if name:
            names = {name}

        # Look for a set as the first argument
        # TODO: remove this! COMPAT w/<1
        elif len(args) > 0 and isinstance(args[0], set):
            show_set_name_warning(get_call_location())
            names = args[0]
            args_copy = list(args)
            args = args[1:]

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

        if state.deploy_name:
            names = {
                '{0} | {1}'.format(state.deploy_name, name)
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
            if state.in_deploy:
                frameinfo = get_caller_frameinfo()
                op_order = state.deploy_op_order + [frameinfo.lineno]
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

        # Add any meta kwargs (sudo, etc) to the meta - first parse any strings
        # as jinja templates.
        actual_global_kwargs = {
            key: get_arg_value(state, host, a)
            for key, a in six.iteritems(global_kwargs)
        }

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
            for key, value in six.iteritems(kwargs):
                if isinstance(value, FunctionType):
                    value = value.__name__

                if key in ('state', 'host'):
                    continue

                arg = '='.join((str(key), str(value)))
                if arg not in op_meta['args']:
                    op_meta['args'].append(arg)

        # Check if we're actually running the operation on this host
        #

        # Run once and we've already added meta for this op? Stop here.
        if op_meta['run_once']:
            has_run = False
            for ops in six.itervalues(state.ops):
                if op_hash in ops:
                    has_run = True
                    break

            if has_run:
                return OperationMeta(op_hash)

        # "Run" operation
        #

        # Otherwise, flag as in-op and run it to get the commands
        state.in_op = True
        state.current_op_hash = op_hash
        state.current_op_global_kwargs = actual_global_kwargs

        # Generate actual arguments by parsing strings as jinja2 templates. This
        # means you can string format arguments w/o generating multiple
        # operations. Only affects top level operations, as must be run "in_op"
        # so facts are gathered correctly.
        actual_args = [
            get_arg_value(state, host, a)
            for a in args
        ]

        actual_kwargs = {
            key: get_arg_value(state, host, a)
            for key, a in six.iteritems(kwargs)
        }

        # Convert to list as the result may be a generator
        commands = unroll_generators(func(*actual_args, **actual_kwargs))
        commands = [  # convert any strings -> StringCommand's
            StringCommand(command.strip())
            if isinstance(command, six.string_types) else command
            for command in commands
        ]

        state.in_op = False
        state.current_op_hash = None
        state.current_op_global_kwargs = None

        # Add host-specific operation data to state
        #

        # We're doing some commands, meta/ops++
        state.meta[host]['ops'] += 1
        state.meta[host]['commands'] += len(commands)

        # Add the server-relevant commands
        state.ops[host][op_hash] = {
            'commands': commands,
            'global_kwargs': actual_global_kwargs,
        }

        # Return result meta for use in deploy scripts
        return OperationMeta(op_hash, commands)

    decorated_func._pyinfra_op = func
    return decorated_func
