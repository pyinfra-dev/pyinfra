# pyinfra
# File: pyinfra/api/deploy.py
# Desc: simple function wrapper that holds and namespaces operations

'''
Deploys come in two forms: on-disk, eg deploy.py, and @deploy wrapped functions.
The latter enable re-usable (across CLI and API based execution) pyinfra extension
creation (eg pyinfra-openstack).
'''

from functools import wraps

import six

from pyinfra import pseudo_host, pseudo_state
from pyinfra.pseudo_modules import PseudoModule

from .host import Host
from .state import State


def add_deploy(state, deploy_func, *args, **kwargs):
    for host in state.inventory:
        # Name the deploy
        deploy_name = getattr(deploy_func, 'deploy_name', deploy_func.__name__)
        with state.named_deploy(deploy_name):
            # Execute the deploy, passing state and host
            deploy_func(state, host, *args, **kwargs)


def deploy(func):
    # If not decorating, return function with config attached
    if isinstance(func, six.string_types):
        def decorator(f):
            setattr(f, 'deploy_name', func)
            return deploy(f)

        return decorator

    # Actually decorate!
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

        # Otherwise (API mode) we just trim off the commands
        else:
            args_copy = list(args)
            state, host = args[0], args[1]
            args = args_copy[2:]

        # Name the deploy
        deploy_name = getattr(func, 'deploy_name', func.__name__)
        with state.named_deploy(deploy_name):
            # Execute the deploy, passing state and host
            func(state, host, *args, **kwargs)

    return decorated_func
