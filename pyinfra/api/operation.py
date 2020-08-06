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
from .exceptions import PyinfraError
from .host import Host
from .inventory import Inventory
from .operation_kwargs import pop_global_op_kwargs
from .state import State
from .util import (
    get_arg_value,
    get_call_location,
    get_caller_frameinfo,
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

    if pyinfra.is_cli and not allow_cli_mode:
        raise PyinfraError((
            '`add_op` should not be called when pyinfra is executing in CLI mode! ({0})'
        ).format(get_call_location()))

    kwargs['frameinfo'] = get_caller_frameinfo()

    # This ensures that every time an operation is added (API mode), it is simply
    # appended to the operation order.
    kwargs['_line_number'] = len(state.op_meta)

    kwargs['state'] = state

    hosts = kwargs.pop('host', state.inventory)
    if not isinstance(hosts, (list, tuple, Inventory)):
        hosts = [hosts]

    results = {}
    for host in hosts:
        kwargs['host'] = host
        results[host] = op_func(*args, **kwargs)

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
        'deprecated, please us `state` and `host` keyword arguments.'
    ).format(call_location))


def operation(func=None, pipeline_facts=None):
    '''
    Decorator that takes a simple module function and turn it into the internal
    operation representation that consists of a list of commands + options
    (sudo, (sudo|su)_user, env).
    '''

    # If not decorating, return function with config attached
    if func is None:
        def decorator(f):
            setattr(f, 'pipeline_facts', pipeline_facts)
            return operation(f)

        return decorator

    # Index the operation!
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

            if not state or not host:
                if not state:
                    raise PyinfraError((
                        'API operation called without state/host: {0} ({1})'
                    ).format(op_name, get_call_location()))

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

        # In API mode we have the kwarg - if a nested operation call we have
        # current_frameinfo.
        frameinfo = kwargs.pop('frameinfo', get_caller_frameinfo())

        # Configure operation
        #

        # Get the meta kwargs (globals that apply to all hosts)
        op_meta_kwargs = pop_global_op_kwargs(state, kwargs)

        # Name the operation
        name = op_meta_kwargs.get('name')
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
            module_bits = func.__module__.split('.')
            module_name = module_bits[-1]
            names = {
                '{0}/{1}'.format(module_name.title(), func.__name__.title()),
            }

        if state.deploy_name:
            names = {
                '{0} | {1}'.format(state.deploy_name, name)
                for name in names
            }

        # If this op is being called inside another, just return here
        # (any unwanted/op-related kwargs removed above).
        if state.in_op:
            return func(*args, **kwargs) or []

        # Inject the current op file number (only incremented in CLI mode)
        op_lines = [state.current_op_file]

        # Add any current @deploy line numbers
        if state.deploy_line_numbers:
            op_lines.extend(state.deploy_line_numbers)

        # Add any current loop count
        if state.loop_line:
            op_lines.extend([state.loop_line, state.loop_counter])

        # Add the line number that called this operation
        line_number = kwargs.pop('_line_number', frameinfo.lineno)
        op_lines.append(line_number)

        # Make a hash from the call stack lines
        op_hash = make_hash(op_lines)

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
            op_lines.append(duplicate_op_count)

        op_lines = tuple(op_lines)

        logger.debug('Adding operation, {0}, called @ {1}:{2}, opLines={3}, opHash={4}'.format(
            names, frameinfo.filename, line_number, op_lines, op_hash,
        ))
        state.op_line_numbers_to_hash[op_lines] = op_hash

        # Ensure shared (between servers) operation meta
        op_meta = state.op_meta.setdefault(op_hash, {
            'names': set(),
            'args': [],
        })

        # Add any meta kwargs (sudo, etc) to the meta - first parse any strings
        # as jinja templates.
        actual_op_meta_kwargs = {
            key: get_arg_value(state, host, a)
            for key, a in six.iteritems(op_meta_kwargs)
        }
        op_meta.update(actual_op_meta_kwargs)

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
                if key in ('state', 'host'):
                    continue

                arg = '='.join((str(key), str(value)))
                if arg not in op_meta['args']:
                    op_meta['args'].append(arg)

        # Check if we're actually running the operation on this host
        #

        # Run once and we've already added meta for this op? Stop here.
        if op_meta_kwargs['run_once']:
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

        # Add host-specific operation data to state
        #

        # We're doing some commands, meta/ops++
        state.meta[host]['ops'] += 1
        state.meta[host]['commands'] += len(commands)

        # Add the server-relevant commands
        state.ops[host][op_hash] = {
            'commands': commands,
        }

        # Return result meta for use in deploy scripts
        return OperationMeta(op_hash, commands)

    decorated_func._pyinfra_op = func
    return decorated_func
