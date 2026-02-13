"""
The Python module allows you to execute Python code within the context of a deploy.
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from typing import Callable

from pyinfra.api import FunctionCommand, QuoteString, StringCommand, operation


@dataclass
class _AnsibleModuleExit(Exception):
    result: dict


@dataclass
class _AnsibleModuleFail(Exception):
    result: dict


class AnsibleModuleAdapter:
    """Best-effort adapter for simple Ansible module functions."""

    def __init__(self, state, host):
        self._state = state
        self._host = host
        self._diff = state.config.DIFF

    def run_command(self, command, **command_kwargs):
        if isinstance(command, (list, tuple)):
            command = StringCommand(*[QuoteString(str(bit)) for bit in command])
        else:
            command = StringCommand(command)

        status, output = self._host.run_shell_command(command, **command_kwargs)
        return (0 if status else 1, output.stdout, output.stderr)

    def fail_json(self, **kwargs):
        raise _AnsibleModuleFail(kwargs)

    def exit_json(self, **kwargs):
        raise _AnsibleModuleExit(kwargs)


def _resolve_ansible_module_src(state, src: str, add_deploy_dir: bool) -> str:
    if add_deploy_dir and state.cwd and not os.path.isabs(src):
        src = os.path.join(state.cwd, src)

    src = os.path.normpath(src)

    if not os.path.isfile(src):
        raise IOError(f"No such file: {src}")

    return src


def _load_ansible_module_function(src: str, function: str):
    module_name = f"pyinfra_ansible_module_{abs(hash((src, function)))}"
    module_spec = importlib.util.spec_from_file_location(module_name, src)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"Cannot import module from: {src}")

    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    module_function = getattr(module, function, None)
    if module_function is None or not callable(module_function):
        raise AttributeError(f"No callable `{function}` found in module: {src}")

    return module_function


def _execute_ansible_module(state, host, src, function, args, kwargs, add_deploy_dir):
    module_src = _resolve_ansible_module_src(state, src, add_deploy_dir)
    module_function = _load_ansible_module_function(module_src, function)
    adapter = AnsibleModuleAdapter(state, host)

    try:
        module_function(adapter, *args, **kwargs)
    except _AnsibleModuleExit:
        return True
    except _AnsibleModuleFail as exc:
        raise RuntimeError(exc.result.get("msg", "Ansible module reported failure")) from None

    return True


@operation(is_idempotent=False, _set_in_op=False)
def call(function: Callable, *args, **kwargs):
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

    yield FunctionCommand(function, args, kwargs)


@operation(is_idempotent=False, _set_in_op=False)
def ansible_module(
    src: str,
    function: str = "main",
    args=(),
    kwargs: dict | None = None,
    add_deploy_dir=True,
):
    """
    Execute a simple Ansible module-style Python function using a pyinfra adapter.

    + src: path to a local Python file containing the module function
    + function: callable name to execute in the module file
    + args: positional arguments passed after the adapter
    + kwargs: keyword arguments passed to the function
    + add_deploy_dir: when true, resolve relative ``src`` from deploy cwd

    This is a best-effort bridge for module functions that accept an adapter object with
    ``run_command``, ``fail_json`` and ``exit_json`` methods.
    """

    yield FunctionCommand(
        _execute_ansible_module,
        (
            src,
            function,
            list(args),
            kwargs or {},
            add_deploy_dir,
        ),
        {},
    )


@operation(is_idempotent=False, _set_in_op=False)
def raise_exception(exception: Exception, *args, **kwargs):
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
        raise exception(*args, **kwargs)  # type: ignore[operator]

    yield FunctionCommand(raise_exc, args, kwargs)
