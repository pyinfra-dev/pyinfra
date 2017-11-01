# pyinfra
# File: pyinfra/api/operation.py
# Desc: wraps deploy script operations and puts commands -> pyinfra._ops

'''
Operations are the core of pyinfra. The ``@operation`` wrapper intercepts calls
to the function and instead diff against the remote server, outputting commands
to the deploy state. This is then run later by pyinfra's ``__main__`` or the
:doc:`./pyinfra.api.operations` module.
'''

from __future__ import unicode_literals

from functools import wraps
from inspect import stack
from os import path
from types import FunctionType

import six

from pyinfra import logger, pseudo_host, pseudo_state
from pyinfra.pseudo_modules import PseudoModule

from .attrs import wrap_attr_data
from .exceptions import PyinfraError
from .host import Host
from .state import State
from .util import get_arg_value, make_hash, pop_op_kwargs, unroll_generators


# List of available operation names
OPERATIONS = []


def get_operation_names():
    '''
    Returns a list of available operations.
    '''

    return OPERATIONS


class OperationMeta(object):
    def __init__(self, hash=None, commands=None):
        self.hash = hash
        self.commands = commands or []

        # Changed flag = did we do anything?
        self.changed = wrap_attr_data('changed', len(self.commands) > 0)


def add_op(state, op_func, *args, **kwargs):
    '''
    Prepare & add an operation to pyinfra.state by executing it on all hosts.

    Args:
        state (``pyinfra.api.State`` obj): the deploy state to add the operation
        to op_func (function): the operation function from one of the modules,
        ie ``server.user``
        args/kwargs: passed to the operation function
    '''

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
    OPERATIONS.append('.'.join((module_name, func.__name__)))

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

            if not state.active:
                return OperationMeta()

            if state.in_op:
                raise PyinfraError((
                    'Nested operation called without state/host: {0}'
                ).format(func))

            if state.in_deploy:
                raise PyinfraError((
                    'Nested deploy operation called without state/host: {0}'
                ).format(func))

        # Otherwise (API mode) we just trim off the commands
        else:
            args_copy = list(args)
            state, host = args[0], args[1]
            args = args_copy[2:]

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

        # Get the meta kwargps (globals that apply to all hosts)
        op_meta_kwargs = pop_op_kwargs(state, kwargs)

        # If this op is being called inside another, just return here
        # (any unwanted/op-related kwargs removed above).
        if state.in_op:
            return func(state, host, *args, **kwargs) or []

        # Get/generate a hash for this op
        op_hash = op_meta_kwargs['op']

        if op_hash is None:
            # Get the line number where this operation was called by looking
            # through the call stack for the first non-pyinfra line. This ensures
            # two identical operations (in terms of arguments/meta) will still
            # generate two hashes.
            frames = stack()
            line_number = None

            for frame in frames:
                if not (
                    frame[3] in ('decorated_func', 'add_op', 'add_limited_op')
                    and frame[1].endswith(path.join('pyinfra', 'api', 'operation.py'))
                ):
                    line_number = frame[0].f_lineno
                    break

            # The when kwarg might change between hosts - but we still want that
            # to count as a single operation. Other meta kwargs are considered
            # "global" and should be the same for every host.
            op_meta_kwargs_copy = op_meta_kwargs.copy()
            op_meta_kwargs_copy.pop('when', None)

            op_hash = make_hash((
                names, line_number, args, kwargs,
                op_meta_kwargs_copy,
            ))

        # Ensure shared (between servers) operation meta
        op_meta = state.op_meta.setdefault(op_hash, {
            'names': set(),
            'args': [],
        })

        # Add any meta kwargs (sudo, etc) to the meta
        op_meta.update(op_meta_kwargs)

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

        # # Add the hash to the operational order if not already in there
        # if op_hash not in state.op_order:
        #     state.op_order.append(op_hash)

        # Add the hash to the operational order if not already in there. To
        # ensure that deploys run as defined in the deploy file *per host* we
        # keep track of each hosts latest op hash, and use that to insert new
        # ones.
        if op_hash not in state.op_order:
            logger.debug((
                'Pushing hash into operation order (host={0}, names={1}): {2}'
            ).format(host.name, names, op_hash))

            previous_op_hash = state.meta[host.name]['latest_op_hash']

            if previous_op_hash:
                # Get the index of the previous op hash and bump after it
                index = state.op_order.index(previous_op_hash) + 1
            else:
                index = 0

            # We *expect* to always append operations - if not it's almost
            # certainly to (mis)use of conditional branches. An unfortunate
            # result of the way deploy files are executed (once per host).
            if index < len(state.op_order):
                logger.warning('''Imbalanced operation detected! ({0})
    Using conditional branches or `host.X` arguments may result in operations
    being called in an unexpected order. Operations will always run in order
    *per host* but branches and variable argument values may cause operations
    to execute in a non-deterministic order.

    Please see: http://pyinfra.readthedocs.io/page/using_python.html.
'''.format(', '.join(names)))

            state.op_order.insert(index, op_hash)

        state.meta[host.name]['latest_op_hash'] = op_hash

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
        state.meta[host.name]['ops'] += 1
        state.meta[host.name]['commands'] += len(commands)

        # Add the server-relevant commands
        state.ops[host.name][op_hash] = {
            'commands': commands,
        }

        # Return result meta for use in deploy scripts
        return OperationMeta(op_hash, commands)

    decorated_func._pyinfra_op = func
    return decorated_func
