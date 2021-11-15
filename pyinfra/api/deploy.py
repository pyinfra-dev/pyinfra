'''
Deploys come in two forms: on-disk, eg deploy.py, and @deploy wrapped functions.
The latter enable re-usable (across CLI and API based execution) pyinfra extension
creation (eg pyinfra-openstack).
'''

from functools import wraps

import six

import pyinfra

from pyinfra import host, logger, pseudo_host, pseudo_state, state

from .exceptions import PyinfraError
from .host import Host
from .operation_kwargs import pop_global_op_kwargs
from .util import get_call_location, get_caller_frameinfo, memoize


@memoize
def show_state_host_arguments_warning(call_location):
    logger.warning((
        '{0}\n\tPassing `state` and `host` as the first two arguments to deploys is '
        'deprecated, please use `state` and `host` arguments.'
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

    hosts = kwargs.pop('host', state.inventory.iter_active_hosts())
    if isinstance(hosts, Host):
        hosts = [hosts]

    # Append operations called in this deploy to the current order
    kwargs['_op_order_number'] = len(state.op_meta)

    with pseudo_state._use(state):
        for deploy_host in hosts:
            with pseudo_host._use(deploy_host):
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
        deploy_kwargs, _ = pop_global_op_kwargs(state, host, kwargs)

        # Name the deploy
        deploy_name = getattr(func, 'deploy_name', func.__name__)
        deploy_data = getattr(func, 'deploy_data', None)

        deploy_op_order = None

        if not pyinfra.is_cli:
            # API mode: `add_deploy` provides the order number
            op_order_number = kwargs.pop('_op_order_number', None)
            if op_order_number is not None:
                deploy_op_order = [op_order_number]
            # API mode: nested deploy wrapped function call
            elif state.deploy_op_order:
                frameinfo = get_caller_frameinfo()
                deploy_op_order = state.deploy_op_order + [frameinfo.lineno]
            else:
                raise PyinfraError((
                    'Operation order number not provided in API mode - '
                    'you must use `add_deploy` to add operations.'
                ))

        with state.deploy(
            name=deploy_name,
            kwargs=deploy_kwargs,
            data=deploy_data,
            deploy_op_order=deploy_op_order,
        ):
            return func(*args, **kwargs)

    return decorated_func
