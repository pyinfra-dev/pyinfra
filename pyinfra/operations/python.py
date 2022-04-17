"""
The Python module allows you to execute Python code within the context of a deploy.
"""

from inspect import getfullargspec

from pyinfra import logger
from pyinfra.api import FunctionCommand, operation
from pyinfra.api.util import get_call_location


@operation(is_idempotent=False)
def call(function, *args, **kwargs):
    """
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
            name="Run my_callback function",
            function=my_callback,
            hello="world",
        )

    """

    argspec = getfullargspec(function)
    if "state" in argspec.args and "host" in argspec.args:
        logger.warning(
            "Callback functions used in `python.call` operations no "
            f"longer take `state` and `host` arguments: {get_call_location(frame_offset=3)}",
        )

    kwargs.pop("state", None)
    kwargs.pop("host", None)
    yield FunctionCommand(function, args, kwargs)


@operation(is_idempotent=False)
def raise_exception(exception, *args, **kwargs):
    def raise_exc(*args, **kwargs):  # pragma: no cover
        raise exception(*args, **kwargs)

    kwargs.pop("state", None)
    kwargs.pop("host", None)
    yield FunctionCommand(raise_exc, args, kwargs)
