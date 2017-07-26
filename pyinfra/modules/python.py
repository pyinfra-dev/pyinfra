# pyinfra
# File: pyinfra/modules/python.py
# Desc: module to enable execution Python code mid-deploy

'''
The Python module allows you to execute Python code within the context of a deploy.
'''

from pyinfra import logger
from pyinfra.api import operation


@operation
def execute(state, host, callback, *args, **kwargs):
    '''
    [DEPRECATED], please use ``python.call``.
    '''

    # COMPAT w/ <0.4
    # TODO: remove this function

    logger.warning((
        'Use of `python.execute` is deprecated, '
        'please use `python.call` instead.'
    ))

    # Pre pyinfra 0.4 the operation execution passed (state, host, host.name)
    # as args, so here we replicate that - hence ``python.call`` which replaces
    # this function going forward.
    args = (host.name,) + args

    yield (callback, args, kwargs)


@operation
def call(state, host, func, *args, **kwargs):
    '''
    Execute a Python function within a deploy.

    + func: the function to execute
    + args: additional arguments to pass to the function
    + kwargs: additional keyword arguments to pass to the function

    Callback functions arge passed the state, host, and any args/kwargs passed
    into the operation directly, eg:

    .. code:: python

        def my_callback(state, host, hello=None):
            ...

        python.call(my_callback, hello='world')

    '''

    yield (func, args, kwargs)
