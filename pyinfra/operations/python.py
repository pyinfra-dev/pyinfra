'''
The Python module allows you to execute Python code within the context of a deploy.
'''

from pyinfra.api import FunctionCommand, operation


@operation
def call(function, *args, **kwargs):
    '''
    Execute a Python function within a deploy.

    + function: the function to execute
    + args: additional arguments to pass to the function
    + kwargs: additional keyword arguments to pass to the function

    Callback functions args passed the state, host, and any args/kwargs passed
    into the operation directly, eg:

    .. code:: python

        def my_callback(state, host, hello=None):
            command = 'echo hello'
            if hello:
                command = command + ' ' + hello

            status, stdout, stderr = host.run_shell_command(command=command, sudo=SUDO)
            assert status is True  # ensure the command executed OK

            if 'hello ' not in '\\n'.join(stdout):  # stdout/stderr is a *list* of lines
                raise Exception(
                    f'`{command}` problem with callback stdout:{stdout} stderr:{stderr}',
                )

        python.call(
            name='Run my_callback function',
            function=my_callback,
            hello='world',
        )

    '''

    kwargs.pop('state', None)
    kwargs.pop('host', None)
    yield FunctionCommand(function, args, kwargs)


@operation
def raise_exception(exception, *args, **kwargs):
    def raise_exc(*args, **kwargs):  # pragma: no cover
        raise exception(*args, **kwargs)

    kwargs.pop('state', None)
    kwargs.pop('host', None)
    yield FunctionCommand(raise_exc, args, kwargs)
