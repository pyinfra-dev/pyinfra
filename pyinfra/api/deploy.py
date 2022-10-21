"""
Deploys come in two forms: on-disk, eg deploy.py, and @deploy wrapped functions.
The latter enable re-usable (across CLI and API based execution) pyinfra extension
creation (eg pyinfra-openstack).
"""

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Union

import pyinfra
from pyinfra import context, logger
from pyinfra.context import ctx_host, ctx_state

from .arguments import pop_global_arguments
from .exceptions import PyinfraError
from .host import Host
from .util import get_args_kwargs_spec, get_call_location, memoize

if TYPE_CHECKING:
    from pyinfra.api.state import State


@memoize
def show_state_host_arguments_warning(call_location):
    logger.warning(
        (
            "{0}:\n\tLegacy deploy function detected! Deploys should no longer define "
            "`state` and `host` arguments."
        ).format(call_location),
    )


def add_deploy(state: "State", deploy_func: Callable[..., Any], *args, **kwargs):
    """
    Prepare & add an deploy to pyinfra.state by executing it on all hosts.

    Args:
        state (``pyinfra.api.State`` obj): the deploy state to add the operation
        deploy_func (function): the operation function from one of the modules,
        ie ``server.user``
        args/kwargs: passed to the operation function
    """

    if pyinfra.is_cli:
        raise PyinfraError(
            (
                "`add_deploy` should not be called when pyinfra is executing in CLI mode! ({0})"
            ).format(get_call_location()),
        )

    hosts = kwargs.pop("host", state.inventory.iter_active_hosts())
    if isinstance(hosts, Host):
        hosts = [hosts]

    with ctx_state.use(state):
        for deploy_host in hosts:
            with ctx_host.use(deploy_host):
                deploy_func(*args, **kwargs)


def deploy(func_or_name: Union[Callable[..., Any], str], data_defaults=None, _call_location=None):
    """
    Decorator that takes a deploy function (normally from a pyinfra_* package)
    and wraps any operations called inside with any deploy-wide kwargs/data.
    """

    # If not decorating, return function with config attached
    if isinstance(func_or_name, str):
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
    # TODO: remove this in v3
    is_legacy = False
    args, kwargs = get_args_kwargs_spec(func)
    if all(key in kwargs and kwargs[key] is None for key in ("state", "host")):
        show_state_host_arguments_warning(_call_location or get_call_location())
        is_legacy = True
    func.is_legacy = is_legacy  # type: ignore

    @wraps(func)
    def decorated_func(*args, **kwargs):
        deploy_kwargs, _ = pop_global_arguments(kwargs)

        # If this is a legacy operation function (ie - state & host arg kwargs), ensure that state
        # and host are included as kwargs.
        if func.is_legacy:
            if "state" not in kwargs:
                kwargs["state"] = context.state
            if "host" not in kwargs:
                kwargs["host"] = context.host
        # If not legacy, pop off any state/host kwargs that may come from legacy @deploy functions
        else:
            kwargs.pop("state", None)
            kwargs.pop("host", None)

        # Name the deploy
        deploy_name = getattr(func, "deploy_name", func.__name__)
        deploy_data = getattr(func, "deploy_data", None)

        with context.host.deploy(
            name=deploy_name,
            kwargs=deploy_kwargs,
            data=deploy_data,
        ):
            return func(*args, **kwargs)

    return decorated_func
