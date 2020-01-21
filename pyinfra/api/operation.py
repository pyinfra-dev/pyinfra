'''
Operations are the core of pyinfra. The ``@operation`` wrapper intercepts calls
to the function and instead diff against the remote server, outputting commands
to the deploy state. This is then run later by pyinfra's ``__main__`` or the
:doc:`./pyinfra.api.operations` module.
'''

from __future__ import unicode_literals

from functools import wraps
from inspect import getframeinfo, stack
from os import path
from types import FunctionType

import six

from pyinfra import logger, pseudo_host, pseudo_state
from pyinfra.pseudo_modules import PseudoModule

from .exceptions import PyinfraError
from .host import Host
from .state import State
from .util import (
    get_arg_value,
    get_caller_frameinfo,
    make_hash,
    pop_global_op_kwargs,
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

    frameinfo = get_caller_frameinfo()
    kwargs['frameinfo'] = frameinfo

    for host in state.inventory:
        op_func(state, host, *args, **kwargs)


def add_limited_op(state, op_func, hosts, *args, **kwargs):
    '''
    DEPRECATED: please use ``add_op`` with the ``hosts`` kwarg.
    '''

    # COMPAT w/ <0.4
    # TODO: remove this function

    logger.warning((
        'Use of `add_limited_op` is deprecated, '
        'please use `add_op` with the `hosts` kwarg instead.'
    ))

    if not isinstance(hosts, (list, tuple)):
        hosts = [hosts]

    # Set the limit
    state.limit_hosts = hosts

    # Add the op
    add_op(state, op_func, *args, **kwargs)

    # Remove the limit
    state.limit_hosts = []


def _get_call_location():
    frames = stack()

    # First two frames are this and the caller below, so get the third item on
    # the frame list, which should be the call to the actual operation.
    frame = getframeinfo(frames[2][0])

    return 'line {0} in {1}'.format(
        frame.lineno,
        path.relpath(frame.filename),
    )


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

        # If we're in CLI mode, there's no state/host passed down, we need to
        # use the global "pseudo" modules.
        if len(args) < 2 or not (
            isinstance(args[0], (State, PseudoModule))
            and isinstance(args[1], (Host, PseudoModule))
        ):
            state = pseudo_state._module
            host = pseudo_host._module

            if state.in_op:
                raise PyinfraError((
                    'Nested operation called without state/host: {0} ({1})'
                ).format(op_name, _get_call_location()))

            if state.in_deploy:
                raise PyinfraError((
                    'Nested deploy operation called without state/host: {0} ({1})'
                ).format(op_name, _get_call_location()))

        # Otherwise (API mode) we just trim off the commands
        else:
            args_copy = list(args)
            state, host = args[0], args[1]
            args = args_copy[2:]

        # In API mode we have the kwarg - if a nested operation call we have
        # current_frameinfo.
        frameinfo = kwargs.pop('frameinfo', get_caller_frameinfo())

        # Configure operation
        #

        # Name the operation
        names = None
        autoname = False

        # Look for a set as the first argument
        if len(args) > 0 and isinstance(args[0], set):
            names = args[0]
            args_copy = list(args)
            args = args[1:]

        # Generate an operation name if needed (Module/Operation format)
        else:
            autoname = True
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

        # Get the meta kwargs (globals that apply to all hosts)
        op_meta_kwargs = pop_global_op_kwargs(state, kwargs)

        # If this op is being called inside another, just return here
        # (any unwanted/op-related kwargs removed above).
        if state.in_op:
            return func(state, host, *args, **kwargs) or []

        line_number = frameinfo.lineno

        # Inject the current op file number (only incremented in CLI mode)
        op_lines = [state.current_op_file]

        # Add any current @deploy line numbers
        if state.deploy_line_numbers:
            op_lines.extend(state.deploy_line_numbers)

        # Add any current loop count
        if state.loop_line:
            op_lines.extend([state.loop_line, state.loop_counter])

        # Add the line number that called this operation
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
        state.op_line_numbers_to_hash[op_lines] = op_hash
        logger.debug('Adding operation, {0}, called @ {1}:{2}, opLines={3}, opHash={4}'.format(
            names, frameinfo.filename, line_number, op_lines, op_hash,
        ))

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
        if autoname:
            for arg in args:
                if isinstance(arg, FunctionType):
                    arg = arg.__name__

                if arg not in op_meta['args']:
                    op_meta['args'].append(arg)

            # Attach keyword args
            for key, value in six.iteritems(kwargs):
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

        # If we're limited, stop here - *after* we've created op_meta. This
        # ensures the meta object always exists, even if no hosts actually ever
        # execute the op (due to limit or otherwise).
        hosts = op_meta_kwargs['hosts']
        when = op_meta_kwargs['when']

        if (
            # Limited by the state's limit_hosts?
            (state.limit_hosts is not None and host not in state.limit_hosts)
            # Limited by the operation kwarg hosts?
            or (hosts is not None and host not in hosts)
            # Limited by the operation kwarg when? We check == because when is
            # normally attribute wrapped as a AttrDataBool, which is actually
            # an integer (Python doesn't allow subclassing bool!).
            or when == False  # noqa
        ):
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
        commands = unroll_generators(func(
            state, host,
            *actual_args,
            **actual_kwargs
        ))

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
