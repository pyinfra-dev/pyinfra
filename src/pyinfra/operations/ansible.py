"""
The Ansible module bridge executes Ansible-style Python modules via pyinfra.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from typing import Any

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


def _get_function_arg_count_from_source(src: str, function: str) -> int:
    with open(src, encoding="utf-8") as source_file:
        module = ast.parse(source_file.read(), filename=src)

    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function:
            arg_count = (
                len(node.args.posonlyargs)
                + len(node.args.args)
                + len(node.args.kwonlyargs)
            )
            if node.args.vararg or node.args.kwarg:
                return arg_count + 1
            return arg_count

    raise AttributeError(f"No callable `{function}` found in module: {src}")


def _get_ansible_module_utils_zip():
    try:
        import ansible  # type: ignore[import-not-found]
        import ansible.module_utils  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised in runtime envs
        raise ImportError(
            "ansible is required to run Ansible modules; install pyinfra[ansible]"
        ) from exc

    ansible_root = os.path.dirname(ansible.__file__)
    module_utils_root = os.path.join(ansible_root, "module_utils")

    if not os.path.isdir(module_utils_root):
        raise RuntimeError(f"Ansible module_utils not found at: {module_utils_root}")

    temp_dir = tempfile.TemporaryDirectory()
    zip_path = os.path.join(temp_dir.name, "ansible_module_utils.zip")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for filename in ("__init__.py", "release.py"):
            source = os.path.join(ansible_root, filename)
            if os.path.isfile(source):
                zip_file.write(source, os.path.join("ansible", filename))

        vendor_root = os.path.join(ansible_root, "_vendor")
        if os.path.isdir(vendor_root):
            for root, _dirs, files in os.walk(vendor_root):
                for file_name in files:
                    source = os.path.join(root, file_name)
                    relpath = os.path.relpath(source, ansible_root)
                    zip_file.write(source, os.path.join("ansible", relpath))

        for root, _dirs, files in os.walk(module_utils_root):
            for file_name in files:
                source = os.path.join(root, file_name)
                relpath = os.path.relpath(source, ansible_root)
                zip_file.write(source, os.path.join("ansible", relpath))

    return temp_dir, zip_path


def _get_remote_python(host):
    if host.connector.__class__.__module__.endswith(".local"):
        return sys.executable

    for candidate in ("python3", "python"):
        status, output = host.run_shell_command(
            StringCommand("sh", "-lc", QuoteString(f"command -v {candidate}")),
        )
        if status and output.stdout.strip():
            return output.stdout.strip().splitlines()[-1]

    raise RuntimeError("No python interpreter found on the target host")


def _parse_ansible_json_output(stdout: str) -> dict[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{") or not line.endswith("}"):
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def _execute_ansible_runtime_module(state, host, src, kwargs, add_deploy_dir):
    module_src = _resolve_ansible_module_src(state, src, add_deploy_dir)
    temp_dir, module_utils_zip = _get_ansible_module_utils_zip()
    remote_dir = None

    try:
        status, output = host.run_shell_command(StringCommand("mktemp", "-d"))
        if not status:
            raise RuntimeError(f"Failed to create remote temp dir: {output.stderr}")

        remote_dir = output.stdout.strip().splitlines()[-1]
        remote_module = f"{remote_dir}/module.py"
        remote_zip = f"{remote_dir}/ansible_module_utils.zip"

        if not host.put_file(module_src, remote_module):
            raise RuntimeError("Failed to upload Ansible module to target host")

        if not host.put_file(module_utils_zip, remote_zip):
            raise RuntimeError("Failed to upload Ansible module_utils to target host")

        python_bin = _get_remote_python(host)
        python_code = (
            "import runpy, sys;"
            f"sys.path.insert(0, {json.dumps(remote_dir)});"
            f"sys.path.insert(0, {json.dumps(remote_zip)});"
            f"runpy.run_path({json.dumps(remote_module)}, run_name='__main__')"
        )

        module_args = json.dumps({"ANSIBLE_MODULE_ARGS": kwargs or {}})
        status, output = host.run_shell_command(
            StringCommand(python_bin, "-c", QuoteString(python_code)),
            _stdin=module_args,
        )

        if status:
            return True

        parsed = _parse_ansible_json_output(output.stdout)
        if parsed and "msg" in parsed:
            raise RuntimeError(str(parsed["msg"]))

        raise RuntimeError(output.stderr or "Ansible module execution failed")
    finally:
        temp_dir.cleanup()
        if remote_dir:
            host.run_shell_command(StringCommand("rm", "-rf", remote_dir))


def _execute_ansible_module(state, host, src, function, args, kwargs, add_deploy_dir):
    module_src = _resolve_ansible_module_src(state, src, add_deploy_dir)
    arg_count = _get_function_arg_count_from_source(module_src, function)
    if arg_count == 0:
        if args:
            raise ValueError("args are not supported for Ansible modules")
        return _execute_ansible_runtime_module(state, host, module_src, kwargs or {}, False)

    try:
        adapter = AnsibleModuleAdapter(state, host)
        module_function = _load_ansible_module_function(module_src, function)
        module_function(adapter, *args, **kwargs)
    except _AnsibleModuleExit:
        return True
    except _AnsibleModuleFail as exc:
        raise RuntimeError(exc.result.get("msg", "Ansible module reported failure")) from None

    return True


@operation(is_idempotent=False, _set_in_op=False)
def module(
    src: str,
    function: str = "main",
    args=(),
    kwargs: dict | None = None,
    add_deploy_dir=True,
    **module_kwargs,
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

    if module_kwargs:
        kwargs = {**(kwargs or {}), **module_kwargs}

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
def ansible_module(
    src: str,
    function: str = "main",
    args=(),
    kwargs: dict | None = None,
    add_deploy_dir=True,
    **module_kwargs,
):
    """
    Backwards-compatible name for the Ansible module runner.
    """

    yield from module(
        src=src,
        function=function,
        args=args,
        kwargs=kwargs,
        add_deploy_dir=add_deploy_dir,
        **module_kwargs,
    )
