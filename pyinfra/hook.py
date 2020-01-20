from functools import wraps

from click import ClickException

from pyinfra.api.exceptions import PyinfraError

from . import logger, pseudo_state

HOOKS = {
    'before_connect': [],
    'before_facts': [],
    'before_deploy': [],
    'after_deploy': [],
}


class Error(PyinfraError, ClickException):
    '''
    Exception raised when encounting errors in deploy hooks.
    '''


def _make_hook_wrapper(hook_name):
    def hook_func(func):
        # Only add hooks when the state is not initialised
        if pseudo_state.initialised:
            return

        # COMPAT
        # TODO: remove this + hooks
        logger.warning((
            'Use of hooks in pyinfra is deprecated, '
            'please use the `python.call` operation instead.'
        ))

        HOOKS[hook_name].append(func)

        @wraps(func)
        def decorated(*args, **kwargs):
            return func(*args, **kwargs)

    return hook_func


before_connect = _make_hook_wrapper('before_connect')
before_facts = _make_hook_wrapper('before_facts')
before_deploy = _make_hook_wrapper('before_deploy')
after_deploy = _make_hook_wrapper('after_deploy')
