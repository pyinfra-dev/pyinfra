'''
Deploys come in two forms: on-disk, eg deploy.py, and @deploy wrapped functions.
The latter enable re-usable (across CLI and API based execution) pyinfra extension
creation (eg pyinfra-openstack).
'''

from functools import wraps

import six

from pyinfra import logger, pseudo_host, pseudo_state
from pyinfra.pseudo_modules import PseudoModule

from .exceptions import PyinfraError
from .host import Host
from .state import State
from .util import get_caller_frameinfo, pop_global_op_kwargs


def add_deploy(state, deploy_func, *args, **kwargs):
    '''
    Prepare & add an deploy to pyinfra.state by executing it on all hosts.

    Args:
        state (``pyinfra.api.State`` obj): the deploy state to add the operation
        deploy_func (function): the operation function from one of the modules,
        ie ``server.user``
        args/kwargs: passed to the operation function
    '''

    frameinfo = get_caller_frameinfo()
    kwargs['frameinfo'] = frameinfo

    for host in state.inventory:
        deploy_func(state, host, *args, **kwargs)


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
        # If we're in CLI mode, there's no state/host passed down, we need to
        # use the global "pseudo" modules.
        if len(args) < 2 or not (
            isinstance(args[0], (State, PseudoModule))
            and isinstance(args[1], (Host, PseudoModule))
        ):
            state = pseudo_state._module
            host = pseudo_host._module

            if state.in_deploy:
                raise PyinfraError((
                    'Nested deploy called without state/host: {0}'
                ).format(func))

        # Otherwise (API mode) we just trim off the commands
        else:
            args_copy = list(args)
            state, host = args[0], args[1]
            args = args_copy[2:]

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

        with state.deploy(deploy_name, deploy_kwargs, deploy_data, frameinfo.lineno):
            # Execute the deploy, passing state and host
            func(state, host, *args, **kwargs)

    return decorated_func
