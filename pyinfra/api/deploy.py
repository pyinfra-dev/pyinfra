'''
Deploys come in two forms: on-disk, eg deploy.py, and @deploy wrapped functions.
The latter enable re-usable (across CLI and API based execution) pyinfra extension
creation (eg pyinfra-openstack).
'''

from functools import wraps

import six

import pyinfra

from pyinfra import host, logger, pseudo_host, pseudo_state, state

from .arguments import pop_global_op_kwargs
from .exceptions import PyinfraError
from .host import Host
from .util import get_args_kwargs_spec, get_call_location, get_caller_frameinfo, memoize


@memoize
def show_state_host_arguments_warning(call_location):
    logger.warning((
        '{0}:\n\tLegacy deploy function detected! Deploys should no longer define '
        '`state` and `host` arguments.'
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


def deploy(func_or_name, data_defaults=None, _call_location=None):
    '''
    Decorator that takes a deploy function (normally from a pyinfra_* package)
    and wraps any operations called inside with any deploy-wide kwargs/data.
    '''

    # If not decorating, return function with config attached
    if isinstance(func_or_name, six.string_types):
        name = func_or_name

        def decorator(f):
            f.deploy_name = name
            if data_defaults:
                f.deploy_data = data_defaults
            return deploy(f, _call_location=get_call_location())
        return decorator

    # Actually decorate!
    func = func_or_name

    # Check whether an operation is "legacy" - ie contains state=None, host=None kwargs
    # TODO: remove this! COMPAT with w/<v2
    is_legacy = False
    args, kwargs = get_args_kwargs_spec(func)
    if all(key in kwargs and kwargs[key] is None for key in ('state', 'host')):
        show_state_host_arguments_warning(_call_location or get_call_location())
        is_legacy = True
    func.is_legacy = is_legacy

    @wraps(func)
    def decorated_func(*args, **kwargs):
        deploy_kwargs, _ = pop_global_op_kwargs(state, host, kwargs)

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
