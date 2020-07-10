'''
Deploys come in two forms: on-disk, eg deploy.py, and @deploy wrapped functions.
The latter enable re-usable (across CLI and API based execution) pyinfra extension
creation (eg pyinfra-openstack).
'''

from functools import wraps

import six

import pyinfra

from pyinfra import logger, pseudo_host, pseudo_state

from .exceptions import PyinfraError
from .host import Host
from .operation_kwargs import pop_global_op_kwargs
from .state import State
from .util import get_call_location, get_caller_frameinfo, memoize


@memoize
def show_state_host_arguments_warning(call_location):
    logger.warning((
        '{0}\n\tPassing `state` and `host` as the first two arguments to deploys is '
        'deprecated, please us `state` and `host` keyword arguments.'
    ).format(call_location))


def add_deploy(state, deploy_func, *args, **kwargs):
    '''
    Prepare & add an deploy to pyinfra.state by executing it on all hosts.

    Args:
        state (``pyinfra.api.State`` obj): the deploy state to add the operation
        deploy_func (function): the operation function from one of the modules,
        ie ``server.user``
        args/kwargs: passed to the operation function
    '''

    if pyinfra.is_cli:
        raise PyinfraError((
            '`add_deploy` should not be called when pyinfra is executing in CLI mode! ({0})'
        ).format(get_call_location()))

    kwargs['frameinfo'] = get_caller_frameinfo()

    # This ensures that ever time a deploy is added (API mode), it is simply
    # appended to the operation order.
    kwargs['_line_number'] = len(state.op_meta)

    kwargs['state'] = state
    for host in state.inventory:
        kwargs['host'] = host
        deploy_func(*args, **kwargs)


def deploy(func_or_name, data_defaults=None):
    '''
    Decorator that takes a deploy function (normally from a pyinfra_* package)
    and wraps any operations called inside with any deploy-wide kwargs/data.
    '''

    # If not decorating, return function with config attached
    if isinstance(func_or_name, six.string_types):
        name = func_or_name

        def decorator(f):
            setattr(f, 'deploy_name', name)

            if data_defaults:
                setattr(f, 'deploy_data', data_defaults)

            return deploy(f)

        return decorator

    # Actually decorate!
    func = func_or_name

    @wraps(func)
    def decorated_func(*args, **kwargs):
        # State & host passed in as kwargs (API, nested op, @deploy op)
        if 'state' in kwargs and 'host' in kwargs:
            state = kwargs.pop('state')
            host = kwargs.pop('host')

        # State & host passed in as first two arguments (LEGACY)
        elif len(args) >= 2 and isinstance(args[0], State) and isinstance(args[1], Host):
            show_state_host_arguments_warning(get_call_location())
            state = args[0]
            host = args[1]
            args_copy = list(args)
            args = args_copy[2:]

        # Finally, still no state+host? Use pseudo if we're CLI mode, or fail
        elif pyinfra.is_cli:
            state = pseudo_state._module
            host = pseudo_host._module

            if state.in_deploy:
                raise PyinfraError((
                    'Nested deploy called without state/host: {0} ({1})'
                ).format(func, get_call_location()))

        else:
            raise PyinfraError((
                'Deploy called without state/host: {0} ({1})'
            ).format(func, get_call_location()))

        # In API mode we have the kwarg - if a nested deploy we actually
        # want the frame of the caller (ie inside the deploy package).
        frameinfo = kwargs.pop('frameinfo', get_caller_frameinfo())
        logger.debug('Adding deploy, called @ {0}:{1}'.format(
            frameinfo.filename, frameinfo.lineno,
        ))

        deploy_kwargs = pop_global_op_kwargs(state, kwargs)

        # Name the deploy
        deploy_name = getattr(func, 'deploy_name', func.__name__)
        deploy_data = getattr(func, 'deploy_data', None)

        line_number = kwargs.pop('_line_number', frameinfo.lineno)

        with state.deploy(deploy_name, deploy_kwargs, deploy_data, line_number):
            # Execute the deploy, passing state and host
            func(state, host, *args, **kwargs)

    return decorated_func
