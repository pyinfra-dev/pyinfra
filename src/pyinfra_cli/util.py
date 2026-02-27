from __future__ import annotations

import json
import os
from datetime import datetime
from inspect import iscoroutine, iscoroutinefunction
from importlib import import_module
from importlib.util import find_spec
from io import IOBase
from os import path
from pathlib import Path
from types import CodeType, FunctionType, ModuleType
from typing import Any, Callable, TYPE_CHECKING

import asyncio
import click

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
from pyinfra.context import ctx_config, ctx_host, ctx_state
from pyinfra.progress import progress_spinner

from .exceptions import CliError, UnexpectedExternalError

# Cache for compiled Python deploy code
PYTHON_CODES: dict[str, CodeType] = {}

if TYPE_CHECKING:
    from pyinfra.api.host import Host


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

        if is_deploy_code:
            run = data.get("run")
            if callable(run):
                if iscoroutinefunction(run):
                    coroutine = run()
                    if not iscoroutine(coroutine):
                        raise TypeError("`run` must return a coroutine when defined as async")
                    asyncio.run(coroutine)
                else:
                    run()
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

    if hasattr(obj, "to_json"):
        return obj.to_json()

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
    elif "." in path:
        # And also a.module.name.function
        mod_path, attr_name = path.rsplit(".", 1)
    else:
        return None

    possible_modules = [mod_path]
    if prefix:
        possible_modules.append(f"{prefix}.{mod_path}")

    module = None

    for possible in possible_modules:
        try:
            # Look for the module/fn, note that from the find_spec doc:
            # "If the name is for submodule (contains a dot), the parent module is
            # automatically imported."
            spec = find_spec(possible)
        except ModuleNotFoundError:
            continue
        except Exception as e:
            # Capture all exceptions here which may be triggered from the automatic module import
            # referenced above the find_spec call.
            logger.warning(f"Exception raised during inventory search on: {possible}: {e}")
            continue
        else:
            if spec is not None:
                module = import_module(possible)
                break

    if module is None:
        if raise_for_none:
            raise CliError(f"No such module: {possible_modules[0]}")
        return

    attr = getattr(module, attr_name, None)
    if attr is None:
        if raise_for_none:
            raise CliError(f"No such attribute in module {possible_modules[0]}: {attr_name}")
        return

    return attr


async def _parallel_load_hosts_async(state: "State", callback: Callable, name: str) -> None:
    def load_file(local_host):
        try:
            with ctx_state.use(state):
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
        except Exception as e:  # noqa: BLE001
            return e
        return None

    hosts = list(state.inventory.iter_active_hosts())

    if not hosts:
        return

    task_to_host = [
        (
            asyncio.create_task(state.run_in_executor(load_file, host)),
            host,
        )
        for host in hosts
    ]

    with progress_spinner(hosts) as progress:

        def _make_progress_callback(target_host: "Host") -> Callable[[asyncio.Future[Any]], None]:
            def _callback(_task: asyncio.Future[Any]) -> None:
                progress(target_host)

            return _callback

        for task, host in task_to_host:
            task.add_done_callback(_make_progress_callback(host))

        results = await asyncio.gather(
            *(task for task, _ in task_to_host),
            return_exceptions=True,
        )

    exceptions: list[Exception] = []

    for (_task, _host), result in zip(task_to_host, results, strict=True):
        if isinstance(result, Exception):
            exceptions.append(result)

    if exceptions:
        raise exceptions[0]


def _parallel_load_hosts(state: "State", callback: Callable, name: str) -> None:
    try:
        asyncio.run(_parallel_load_hosts_async(state, callback, name))
    except RuntimeError as exc:
        if "already running" in str(exc):
            raise RuntimeError(
                "Parallel host loading cannot run while an asyncio loop is active. "
                "Use the async helper instead.",
            ) from exc
        raise


def load_deploy_file(state: "State", filename):
    state.current_deploy_filename = filename
    _parallel_load_hosts(state, lambda: exec_file(filename, is_deploy_code=True), filename)


def load_func(state: "State", op_func, *args, **kwargs):
    _parallel_load_hosts(state, lambda: op_func(*args, **kwargs), op_func.__name__)
