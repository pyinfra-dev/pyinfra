from __future__ import annotations

import asyncio
import contextvars
import os
from pathlib import Path
from random import shuffle

from pyinfra.context import ctx_inventory, ctx_state

import inspect

from .util import run_cli


TESTS_DIR = Path(__file__).resolve().parent
DEPLOY_DIR = TESTS_DIR / "deploy"
A_TASK_FILE = "tasks/a_task.py"
ANOTHER_TASK_FILE = "tasks/another_task.py"
B_TASK_FILE = "tasks/b_task.py"


EXPECTED_DEPLOY_OPS = [
    ("First main operation", True),
    ("Second main operation", ("somehost",)),
    (f"{A_TASK_FILE} | First task operation", ("anotherhost",)),
    (f"{A_TASK_FILE} | Task order loop 1", ("anotherhost",)),
    (f"{A_TASK_FILE} | 2nd Task order loop 1", ("anotherhost",)),
    (f"{A_TASK_FILE} | Task order loop 2", ("anotherhost",)),
    (f"{A_TASK_FILE} | 2nd Task order loop 2", ("anotherhost",)),
    (
        f"{A_TASK_FILE} | {ANOTHER_TASK_FILE} | Second task operation",
        ("anotherhost",),
    ),
    (f"{A_TASK_FILE} | First task operation", True),
    (f"{A_TASK_FILE} | Task order loop 1", True),
    (f"{A_TASK_FILE} | 2nd Task order loop 1", True),
    (f"{A_TASK_FILE} | Task order loop 2", True),
    (f"{A_TASK_FILE} | 2nd Task order loop 2", True),
    (f"{A_TASK_FILE} | {ANOTHER_TASK_FILE} | Second task operation", True),
    (f"{B_TASK_FILE} | Important task operation", True),
    ("My deploy | First deploy operation", True),
    ("My deploy | My nested deploy | First nested deploy operation", True),
    ("My deploy | Second deploy operation", True),
    ("Loop-0 main operation", True),
    ("Loop-1 main operation", True),
    ("Third main operation", True),
    ("Order loop 1", True),
    ("Nested order loop 1/1", ("anotherhost",)),
    ("Nested order loop 1/2", ("anotherhost",)),
    ("Order loop 2", True),
    ("Nested order loop 2/1", ("somehost", "anotherhost")),
    ("Nested order loop 2/2", ("somehost", "anotherhost")),
    ("Final limited operation", ("somehost",)),
    ("Second final limited operation", ("anotherhost", "someotherhost")),
]


EXPECTED_RANDOM_OPS = [
    ("First main operation", True),
    ("Second main somehost operation", ("somehost",)),
    ("Second main anotherhost operation", ("anotherhost",)),
    ("Function call operation", True),
    ("Third main operation", True),
    ("First nested operation", True),
    ("Second nested anotherhost operation", ("anotherhost",)),
    ("Second nested somehost operation", ("somehost",)),
]


EXPECTED_ASYNC_OPS = [
    ("Async main operation", True),
    ("Async second operation", True),
]


EXPECTED_SYNC_RUN_OPS = [
    ("Sync run main operation", True),
    ("Sync run second operation", True),
]


def _patch_sync_executor(monkeypatch):
    async def _run_in_executor_sync(self, func, *args, **kwargs):
        bound_self = getattr(func, "__self__", None)
        name = getattr(func, "__name__", "")

        if bound_self is not None:
            if name == "connect":
                return await bound_self.connect_async(*args, **kwargs)
            if name == "disconnect":
                return await bound_self.disconnect_async(*args, **kwargs)

        loop = asyncio.get_running_loop()
        context = contextvars.copy_context()

        def _call_in_thread():
            result = context.run(func, *args, **kwargs)
            if inspect.isawaitable(result):
                return context.run(asyncio.run, result)
            return result

        executor = getattr(self, "executor", None)
        if executor is None:
            raise RuntimeError("State executor not initialised")

        return await loop.run_in_executor(executor, _call_in_thread)

    monkeypatch.setattr(
        "pyinfra.api.state.State.run_in_executor",
        _run_in_executor_sync,
        raising=False,
    )


def _write_inventory_file(inventory_path: Path, hosts: list[str]) -> Path:
    lines = ["hosts = (", "    ["]
    for host in hosts:
        lines.append(f'        "{host}",')
    lines.extend(["    ],", "    {},", ")", ""])
    inventory_path.write_text("\n".join(lines))
    return inventory_path


def _run_cli(inventory_path: Path, filename: str):
    return run_cli(
        "-y",
        "--parallel=1",
        str(inventory_path),
        str(DEPLOY_DIR / filename),
        f"--chdir={DEPLOY_DIR}",
    )


def _assert_operation_execution(expected, state):
    op_order = state.get_op_order()
    assert len(op_order) == len(expected)

    for op_hash, (expected_name, expected_hosts) in zip(op_order, expected, strict=True):
        op_meta = state.op_meta[op_hash]
        actual_name = next(iter(op_meta.names))
        normalised_actual = actual_name.replace(os.sep, "/")
        normalised_expected = expected_name.replace(os.sep, "/")
        assert normalised_actual == normalised_expected

        for host in state.inventory:
            host_op = state.ops[host].get(op_hash)
            executed = bool(host_op and host_op.operation_meta.executed)

            if expected_hosts is True:
                assert executed is True
            else:
                assert executed is (host.name in expected_hosts)


def test_deploy_preserves_operation_order(tmp_path, fake_asyncssh, monkeypatch):
    _patch_sync_executor(monkeypatch)
    hosts = ["somehost", "anotherhost", "someotherhost"]

    for iteration in range(3):
        fake_asyncssh.clear()

        try:
            shuffled_hosts = hosts.copy()
            shuffle(shuffled_hosts)
            inventory_file = _write_inventory_file(
                tmp_path / f"deploy_inventory_{iteration}.py",
                shuffled_hosts,
            )

            result = _run_cli(inventory_file, "deploy.py")
            assert result.exit_code == 0, result.stdout

            state = ctx_state.get()
            assert state is not None
            _assert_operation_execution(EXPECTED_DEPLOY_OPS, state)

            assert set(fake_asyncssh.keys()) == set(hosts)
            for connection in fake_asyncssh.values():
                assert connection.commands_run
        finally:
            ctx_state.reset()
            ctx_inventory.reset()


def test_random_deploy_is_consistent(tmp_path, fake_asyncssh, monkeypatch):
    _patch_sync_executor(monkeypatch)
    hosts = ["somehost", "anotherhost", "someotherhost"]

    for iteration in range(3):
        fake_asyncssh.clear()

        try:
            shuffled_hosts = hosts.copy()
            shuffle(shuffled_hosts)
            inventory_file = _write_inventory_file(
                tmp_path / f"random_inventory_{iteration}.py",
                shuffled_hosts,
            )

            result = _run_cli(inventory_file, "deploy_random.py")
            assert result.exit_code == 0, result.stdout

            state = ctx_state.get()
            assert state is not None
            _assert_operation_execution(EXPECTED_RANDOM_OPS, state)

            assert set(fake_asyncssh.keys()) == set(hosts)
            for connection in fake_asyncssh.values():
                assert connection.commands_run
        finally:
            ctx_state.reset()
            ctx_inventory.reset()


def test_async_run_deploy_is_consistent(tmp_path, fake_asyncssh, monkeypatch):
    _patch_sync_executor(monkeypatch)
    hosts = ["somehost", "anotherhost", "someotherhost"]

    for iteration in range(3):
        fake_asyncssh.clear()

        try:
            shuffled_hosts = hosts.copy()
            shuffle(shuffled_hosts)
            inventory_file = _write_inventory_file(
                tmp_path / f"async_inventory_{iteration}.py",
                shuffled_hosts,
            )

            result = _run_cli(inventory_file, "deploy_async.py")
            assert result.exit_code == 0, result.stdout

            state = ctx_state.get()
            assert state is not None
            _assert_operation_execution(EXPECTED_ASYNC_OPS, state)

            assert set(fake_asyncssh.keys()) == set(hosts)
            for connection in fake_asyncssh.values():
                assert connection.commands_run
        finally:
            ctx_state.reset()
            ctx_inventory.reset()


def test_sync_run_deploy_is_consistent(tmp_path, fake_asyncssh, monkeypatch):
    _patch_sync_executor(monkeypatch)
    hosts = ["somehost", "anotherhost", "someotherhost"]

    for iteration in range(3):
        fake_asyncssh.clear()

        try:
            shuffled_hosts = hosts.copy()
            shuffle(shuffled_hosts)
            inventory_file = _write_inventory_file(
                tmp_path / f"sync_run_inventory_{iteration}.py",
                shuffled_hosts,
            )

            result = _run_cli(inventory_file, "deploy_sync_run.py")
            assert result.exit_code == 0, result.stdout

            state = ctx_state.get()
            assert state is not None
            _assert_operation_execution(EXPECTED_SYNC_RUN_OPS, state)

            assert set(fake_asyncssh.keys()) == set(hosts)
            for connection in fake_asyncssh.values():
                assert connection.commands_run
        finally:
            ctx_state.reset()
            ctx_inventory.reset()
