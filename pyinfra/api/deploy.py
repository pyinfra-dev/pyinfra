"""
Deploys come in two forms: on-disk, eg deploy.py, and @deploy wrapped functions.
The latter enable re-usable (across CLI and API based execution) pyinfra extension
creation (eg pyinfra-openstack).
"""

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional, cast

from typing_extensions import ParamSpec

import pyinfra
from pyinfra import context
from pyinfra.context import ctx_host, ctx_state

from .arguments import pop_global_arguments
from .arguments_typed import PyinfraOperation
from .exceptions import PyinfraError
from .host import Host
from .util import get_call_location

if TYPE_CHECKING:
    from pyinfra.api.state import State


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


P = ParamSpec("P")


def deploy(name: Optional[str] = None, data_defaults=None):
    """
    Decorator that takes a deploy function (normally from a pyinfra_* package)
    and wraps any operations called inside with any deploy-wide kwargs/data.
    """

    def decorator(func: Callable[P, Any]) -> PyinfraOperation[P]:
        func.deploy_name = name or func.__name__  # type: ignore[attr-defined]
        if data_defaults:
            func.deploy_data = data_defaults  # type: ignore[attr-defined]
        return _wrap_deploy(func)

    return decorator


def _wrap_deploy(func: Callable[P, Any]) -> PyinfraOperation[P]:
    @wraps(func)
    def decorated_func(*args: P.args, **kwargs: P.kwargs) -> Any:
        deploy_kwargs, _ = pop_global_arguments(kwargs)

        deploy_data = getattr(func, "deploy_data", None)

        with context.host.deploy(
            name=func.deploy_name,  # type: ignore[attr-defined]
            kwargs=deploy_kwargs,
            data=deploy_data,
        ):
            return func(*args, **kwargs)

    decorated_func._inner = func  # type: ignore[attr-defined]
    return cast(PyinfraOperation[P], decorated_func)
