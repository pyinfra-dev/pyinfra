# pyinfra
# File: pyinfra/hook.py
# Desc: Python hooks for CLI deploys

from functools import wraps

from . import pseudo_state

HOOKS = {
    'before_connect': [],
    'before_facts': [],
    'before_deploy': [],
    'after_deploy': [],
}


class Error(Exception):
    '''
    Exception raised when encounting errors in deploy hooks.
    '''


def _make_hook_wrapper(hook_name):
    def hook_func(func):
        # Only add hooks when the state isn't active
        if pseudo_state.active:
            return

        HOOKS[hook_name].append(func)

        @wraps(func)
        def decorated(*args, **kwargs):
            return func(*args, **kwargs)

    return hook_func


before_connect = _make_hook_wrapper('before_connect')
before_facts = _make_hook_wrapper('before_facts')
before_deploy = _make_hook_wrapper('before_deploy')
after_deploy = _make_hook_wrapper('after_deploy')
