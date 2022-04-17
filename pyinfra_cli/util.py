import json
import os
from datetime import datetime
from importlib import import_module
from os import path
from types import FunctionType, ModuleType

# py2/3 switcheroo
try:
    from types import FileType

    from cStringIO import InputType, OutputType
    from StringIO import StringIO

    io_bases = (FileType, OutputType, InputType, StringIO)

except ImportError:  # pragma: no cover
    from io import IOBase

    io_bases = IOBase

import click
import gevent

from pyinfra import logger, state
from pyinfra.api.command import PyinfraCommand
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.host import HostData
from pyinfra.api.operation import OperationMeta
from pyinfra.context import ctx_config, ctx_host
from pyinfra.progress import progress_spinner

from .exceptions import CliError, UnexpectedExternalError

# Cache for compiled Python deploy code
PYTHON_CODES = {}


def is_subdir(child, parent):
    child = path.realpath(child)
    parent = path.realpath(parent)
    relative = path.relpath(child, start=parent)
    return not relative.startswith(os.pardir)


def exec_file(filename, return_locals=False, is_deploy_code=False):
    """
    Execute a Python file and optionally return it's attributes as a dict.
    """

    old_current_exec_filename = state.current_exec_filename
    state.current_exec_filename = filename

    if filename not in PYTHON_CODES:
        with open(filename, "r") as f:
            code = f.read()

        code = compile(code, filename, "exec")
        PYTHON_CODES[filename] = code

    # Create some base attributes for our "module"
    data = {
        "__file__": filename,
    }

    # Execute the code with locals/globals going into the dict above
    try:
        exec(PYTHON_CODES[filename], data)
    except Exception as e:
        if isinstance(e, PyinfraError):
            raise
        raise UnexpectedExternalError(e, filename)

    state.current_exec_filename = old_current_exec_filename
    return data


def json_encode(obj):
    # pyinfra types
    if isinstance(obj, HostData):
        return obj.dict()

    elif isinstance(obj, PyinfraCommand):
        return repr(obj)

    elif isinstance(obj, OperationMeta):
        return repr(obj)

    # Python types
    elif isinstance(obj, ModuleType):
        return "Module: {0}".format(obj.__name__)

    elif isinstance(obj, FunctionType):
        return "Function: {0}".format(obj.__name__)

    elif isinstance(obj, datetime):
        return obj.isoformat()

    elif isinstance(obj, io_bases):
        if hasattr(obj, "name"):
            return "File: {0}".format(obj.name)

        elif hasattr(obj, "template"):
            return "Template: {0}".format(obj.template)

        obj.seek(0)
        return "In memory file: {0}".format(obj.read())

    elif isinstance(obj, set):
        return sorted(list(obj))

    elif isinstance(obj, bytes):
        return obj.decode()

    else:
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


def get_operation_and_args(commands):
    operation_name = commands[0]

    # Get the module & operation name
    op_module, op_name = operation_name.rsplit(".", 1)

    # Try to load the requested operation from the main operations package.
    # If that fails, try to load from the user's operations package.
    try:
        op_module = import_module("pyinfra.operations.{0}".format(op_module))
    except ImportError:
        try:
            op_module = import_module(str(op_module))
        except ImportError:
            raise CliError("No such module: {0}".format(op_module))

    op = getattr(op_module, op_name, None)
    if not op:
        raise CliError("No such operation: {0}".format(operation_name))

    # Parse the arguments
    operation_args = commands[1:]

    if len(operation_args) == 1:
        # Check if we're JSON (in which case we expect a list of two items:
        # a list of args and a dict of kwargs).
        try:
            args, kwargs = json.loads(operation_args[0])
            return op, (args or (), kwargs or {})
        except ValueError:
            pass

    args = [parse_cli_arg(arg) for arg in operation_args if "=" not in arg]

    kwargs = {
        key: parse_cli_arg(value)
        for key, value in [arg.split("=", 1) for arg in operation_args if "=" in arg]
    }

    return op, (args, kwargs)


def get_facts_and_args(commands):
    facts = []

    current_fact = None

    for command in commands:
        if "=" in command:
            if not current_fact:
                raise CliError("Invalid fact commands: `{0}`".format(commands))

            key, value = command.split("=", 1)
            current_fact[2][key] = value
            continue

        if current_fact:
            facts.append(current_fact)
            current_fact = None

        if "." not in command:
            raise CliError(f"Invalid fact: `{command}`, should be in the format `module.cls`")

        fact_module, fact_name = command.rsplit(".", 1)
        try:
            fact_module = import_module("pyinfra.facts.{0}".format(fact_module))
        except ImportError:
            try:
                fact_module = import_module(str(fact_module))
            except ImportError:
                raise CliError("No such module: `{0}`".format(fact_module))

        fact_cls = getattr(fact_module, fact_name, None)
        if not fact_cls:
            raise CliError("No such fact: `{0}`".format(command))

        current_fact = (fact_cls, (), {})

    if current_fact:
        facts.append(current_fact)

    return facts


def load_deploy_file(state, filename):
    state.current_deploy_filename = filename

    def load_file(local_host):
        with ctx_config.use(state.config.copy()):
            with ctx_host.use(local_host):
                exec_file(filename)
                logger.info(
                    "{0}{1} {2}".format(
                        local_host.print_prefix,
                        click.style("Ready:", "green"),
                        click.style(filename, bold=True),
                    ),
                )

    greenlet_to_host = {
        state.pool.spawn(load_file, host): host for host in state.inventory.iter_active_hosts()
    }

    with progress_spinner(greenlet_to_host.values()) as progress:
        for greenlet in gevent.iwait(greenlet_to_host.keys()):
            host = greenlet_to_host[greenlet]
            greenlet.get()
            progress(host)
