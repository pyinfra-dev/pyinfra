# pyinfra
# File: pyinfra/hook.py

from functools import wraps

HOOK_NAMES = ('before_connect', 'before_facts', 'before_deploy', 'after_deploy')

HOOKS = {
    key: []
    for key in HOOK_NAMES
}


def before_connect(func):
    HOOKS['before_connect'].append(func)

    @wraps(func)
    def decorated(*args, **kwargs):
        return func(*args, **kwargs)


def before_facts(func):
    HOOKS['before_facts'].append(func)

    @wraps(func)
    def decorated(*args, **kwargs):
        return func(*args, **kwargs)


def before_deploy(func):
    HOOKS['before_deploy'].append(func)

    @wraps(func)
    def decorated(*args, **kwargs):
        return func(*args, **kwargs)


def after_deploy(func):
    HOOKS['after_deploy'].append(func)

    @wraps(func)
    def decorated(*args, **kwargs):
        return func(*args, **kwargs)
