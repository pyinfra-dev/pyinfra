from __future__ import annotations

import json
import os
from datetime import datetime
from importlib import import_module
from importlib.util import find_spec
from io import IOBase
from os import path
from pathlib import Path
from types import CodeType, FunctionType, ModuleType
from typing import Callable

import click
import gevent

from pyinfra import logger, state
from pyinfra.api.command import PyinfraCommand
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.host import HostData
from pyinfra.api.operation import OperationMeta
from pyinfra.api.state import (
    State,
    StateHostMeta,
    StateHostResults,
    StateOperationHostData,
    StateOperationMeta,
)
from pyinfra.context import ctx_config, ctx_host
from pyinfra.progress import progress_spinner

from .exceptions import CliError, UnexpectedExternalError

# Cache for compiled Python deploy code
PYTHON_CODES: dict[str, CodeType] = {}


def is_subdir(child, parent):
    child = path.realpath(child)
    parent = path.realpath(parent)
    relative = path.relpath(child, start=parent)
    return not relative.startswith(os.pardir)


def exec_file(filename, return_locals: bool = False, is_deploy_code: bool = False):
    """
    Execute a Python file and optionally return it's attributes as a dict.
    """

    old_current_exec_filename = state.current_exec_filename
    state.current_exec_filename = filename

    if filename not in PYTHON_CODES:
        with open(filename, "r", encoding="utf-8") as f:
            code_str = f.read()

        code = compile(code_str, filename, "exec")
        PYTHON_CODES[filename] = code

    # Create some base attributes for our "module"
    data = {"__file__": filename}

    # Execute the code with locals/globals going into the dict above
    try:
        exec(PYTHON_CODES[filename], data)
    except PyinfraError:
        # Raise pyinfra errors as-is
        raise
    except Exception as e:
        # Wrap & re-raise errors in user code so we highlight filename/etc
        raise UnexpectedExternalError(e, filename)
    finally:
        state.current_exec_filename = old_current_exec_filename

    return data


def json_encode(obj):
    # pyinfra types
    if isinstance(obj, HostData):
        return obj.dict()

    if isinstance(obj, PyinfraCommand):
        return repr(obj)

    if isinstance(
        obj,
        (
            OperationMeta,
            StateOperationMeta,
            StateOperationHostData,
            StateHostMeta,
            StateHostResults,
        ),
    ):
        return repr(obj)

    # Python types
    if isinstance(obj, ModuleType):
        return "Module: {0}".format(obj.__name__)

    if isinstance(obj, FunctionType):
        return "Function: {0}".format(obj.__name__)

    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, IOBase):
        if hasattr(obj, "name"):
            return "File: {0}".format(obj.name)

        if hasattr(obj, "template"):
            return "Template: {0}".format(obj.template)

        obj.seek(0)
        return "In memory file: {0}".format(obj.read())

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, set):
        return sorted(list(obj))

    if isinstance(obj, bytes):
        return obj.decode()

    raise TypeError("Cannot serialize: {0} ({1})".format(type(obj), obj))


def parse_cli_arg(arg):
    if isinstance(arg, list):
        return [parse_cli_arg(a) for a in arg]

    if arg.lower() == "false":
        return False

    if arg.lower() == "true":
        return True

    try:
        return int(arg)
    except (TypeError, ValueError):
        pass

    try:
        return json.loads(arg)
    except ValueError:
        pass

    return arg


def try_import_module_attribute(path, prefix=None, raise_for_none=True):
    if ":" in path:
        # Allow a.module.name:function syntax
        mod_path, attr_name = path.rsplit(":", 1)
    else:
        # And also a.module.name.function
        mod_path, attr_name = path.rsplit(".", 1)

    possible_modules = [mod_path]
    if prefix:
        possible_modules.append(f"{prefix}.{mod_path}")

    module = None

    for possible in possible_modules:
        try:
            # First use find_spec which checks if the possible module exists *without* importing
            # it, thus any import errors it contains still get properly raised to the user.
            spec = find_spec(possible)
        except ModuleNotFoundError:
            continue
        else:
            if spec is not None:
                module = import_module(possible)
                break

    if module is None:
        if raise_for_none:
            raise CliError(f"No such module: {possible_modules[-1]}")
        return

    attr = getattr(module, attr_name, None)
    if attr is None:
        if raise_for_none:
            raise CliError(f"No such attribute in module {possible_modules[-1]}: {attr_name}")
        return

    return attr


def _parallel_load_hosts(state: "State", callback: Callable, name: str):
    def load_file(local_host):
        try:
            with ctx_config.use(state.config.copy()):
                with ctx_host.use(local_host):
                    callback()
                    logger.info(
                        "{0}{1} {2}".format(
                            local_host.print_prefix,
                            click.style("Ready:", "green"),
                            click.style(name, bold=True),
                        ),
                    )
        except Exception as e:
            return e

    greenlet_to_host = {
        state.pool.spawn(load_file, host): host for host in state.inventory.iter_active_hosts()
    }

    with progress_spinner(greenlet_to_host.values()) as progress:
        for greenlet in gevent.iwait(greenlet_to_host.keys()):
            host = greenlet_to_host[greenlet]
            result = greenlet.get()
            if isinstance(result, Exception):
                raise result
            progress(host)


def load_deploy_file(state: "State", filename):
    state.current_deploy_filename = filename
    _parallel_load_hosts(state, lambda: exec_file(filename), filename)


def load_func(state: "State", op_func, *args, **kwargs):
    _parallel_load_hosts(state, lambda: op_func(*args, **kwargs), op_func.__name__)
