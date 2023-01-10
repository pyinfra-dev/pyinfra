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
    + args: arguments to pass to the function
    + kwargs: keyword arguments to pass to the function

    **Example:**

    .. code:: python

        def my_callback(hello=None):
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
    """
    Raise a Python exception within a deploy.

    + exception: the exception class to raise
    + args: arguments passed to the exception creation
    + kwargs: keyword arguments passed to the exception creation

    **Example**:

    .. code:: python

        python.raise_exception(
            name="Raise NotImplementedError exception",
            exception=NotImplementedError,
            message="This is not implemented",
        )
    """

    def raise_exc(*args, **kwargs):  # pragma: no cover
        raise exception(*args, **kwargs)

    kwargs.pop("state", None)
    kwargs.pop("host", None)
    yield FunctionCommand(raise_exc, args, kwargs)
