'''
The Python module allows you to execute Python code within the context of a deploy.
'''

from pyinfra.api import operation


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


@operation
def raise_exception(state, host, exception_class, *args, **kwargs):
    def raise_exc(*args, **kwargs):  # pragma: no cover
        raise exception_class(*args, **kwargs)

    yield (raise_exc, args, kwargs)
