import asyncio
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch

from pyinfra import context
from pyinfra.api import Config, FunctionCommand, Inventory, State, StringCommand, operation
from pyinfra.api.concurrency import (
    NoGreenletContext,
    async_def,
    awaitlet,
    in_greenlet,
    iterate_async_generator,
    run_coroutine,
    run_for_hosts,
    run_with_timeout,
)
from pyinfra.api.connect import connect_all
from pyinfra.api.deploy import add_deploy, deploy
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.api.state import StateStage
from pyinfra.connectors.util import CommandOutput, OutputLine
from pyinfra.facts.server import Command
from pyinfra.operations import python

from ..fake_ssh import AsyncPatchSSHTestCase
from ..util import make_inventory


class TestConcurrencyHelpers(IsolatedAsyncioTestCase):
    async def test_awaitlet_from_greenlet(self):
        def sync_function():
            assert in_greenlet()
            return awaitlet(asyncio.sleep(0, result="hello"))

        assert not in_greenlet()
        assert await async_def(sync_function) == "hello"

    async def test_awaitlet_outside_greenlet_raises(self):
        with self.assertRaises(NoGreenletContext):
            awaitlet(asyncio.sleep(0))

    async def test_run_coroutine_mixes_sync_and_async(self):
        def sync_io():
            return awaitlet(asyncio.sleep(0, result="io"))

        async def coroutine():
            await asyncio.sleep(0)
            return sync_io()

        assert await async_def(lambda: run_coroutine(coroutine())) == "io"

    async def test_run_coroutine_propagates_exceptions(self):
        async def coroutine():
            await asyncio.sleep(0)
            raise KeyError("boom")

        with self.assertRaises(KeyError):
            await async_def(lambda: run_coroutine(coroutine()))

    async def test_run_with_timeout(self):
        async def slow():
            await asyncio.sleep(10)

        with self.assertRaises(TimeoutError):
            await async_def(lambda: run_with_timeout(lambda: run_coroutine(slow()), 0.01))

        assert await async_def(lambda: run_with_timeout(lambda: "done", 0.01)) == "done"
        assert await async_def(lambda: run_with_timeout(lambda: "done", None)) == "done"

    async def test_iterate_async_generator_closes_when_abandoned(self):
        closed = []

        async def generate():
            try:
                yield 1
                yield 2
            finally:
                closed.append(True)

        def take_first():
            for item in iterate_async_generator(generate()):
                return item

        assert await async_def(take_first) == 1
        assert closed == [True]

    def test_iterate_async_generator_outside_greenlet(self):
        async def generate():
            await asyncio.sleep(0)
            yield 1
            yield 2

        assert list(iterate_async_generator(generate())) == [1, 2]

    async def test_run_for_hosts(self):
        def work(host, suffix):
            awaitlet(asyncio.sleep(0))
            return f"{host}-{suffix}"

        results = await run_for_hosts(["a", "b"], work, "done", parallel=1)
        assert results == {"a": "a-done", "b": "b-done"}

    async def test_run_for_hosts_raises_first_error_after_all_complete(self):
        completed = []

        def work(host):
            awaitlet(asyncio.sleep(0))
            if host == "a":
                raise ValueError(host)
            completed.append(host)

        with self.assertRaises(ValueError):
            await run_for_hosts(["a", "b"], work)

        assert completed == ["b"]


class TestAsyncOperations(AsyncPatchSSHTestCase):
    async def test_async_operation_and_callback(self):
        inventory = make_inventory(hosts=("somehost",))
        state = State(inventory, Config())
        state.current_stage = StateStage.Prepare
        await connect_all(state)

        seen = []

        @operation()
        async def wait_for_thing(name):
            await asyncio.sleep(0)
            # Synchronous host APIs work inside async operations
            seen.append(context.host.get_fact(Command, "echo hi"))

            async def callback(state, host):
                await asyncio.sleep(0)
                seen.append(host.get_fact(Command, "echo callback"))

            yield StringCommand("echo", name)
            yield FunctionCommand(callback, (), {})

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = (True, CommandOutput([OutputLine("stdout", "out")]))

            await add_op(state, wait_for_thing, "thing")
            await run_ops(state)

        # Once during change detection (prepare), twice during execute
        assert seen == ["out", "out", "out"]
        somehost = inventory.get_host("somehost")
        assert state.results[somehost].success_ops == 1

    async def test_async_python_call(self):
        inventory = make_inventory(hosts=("somehost",))
        state = State(inventory, Config())
        state.current_stage = StateStage.Prepare
        await connect_all(state)

        called = []

        async def callback(greeting):
            await asyncio.sleep(0)
            called.append(greeting)

        await add_op(state, python.call, callback, "hello")
        await run_ops(state)

        assert called == ["hello"]
        somehost = inventory.get_host("somehost")
        assert state.results[somehost].success_ops == 1

    async def test_sync_api_from_async_code_raises(self):
        inventory = make_inventory(hosts=("somehost",))
        State(inventory, Config())
        host = inventory.get_host("somehost")
        await async_def(host.connect)

        with self.assertRaises(NoGreenletContext):
            host.run_shell_command("echo hi")


class TestAsyncOperationInner(TestCase):
    def test_inner_of_async_operation_is_a_generator(self):
        @operation()
        async def async_op():
            await asyncio.sleep(0)
            yield StringCommand("echo", "async")

        @operation()
        def sync_op():
            yield from async_op._inner()
            yield StringCommand("echo", "sync")

        commands = list(sync_op._inner())
        assert [str(command) for command in commands] == ["echo async", "echo sync"]


class TestApiPreparation(IsolatedAsyncioTestCase):
    async def test_run_once_after_fact_io(self):
        @operation()
        def run_once_operation():
            context.host.get_fact(Command, "echo ready")
            yield StringCommand("echo once")

        @deploy()
        def run_once_deploy():
            run_once_operation(_run_once=True)

        for use_deploy in (False, True):
            with self.subTest(use_deploy=use_deploy):
                inventory = Inventory(
                    (["@fake/first", "@fake/second"], {}),
                    override_data={"fake_delay": 0.001, "fake_delay_jitter": 0.0},
                )
                state = State(inventory, Config())
                await connect_all(state)
                first, second = inventory.get_active_hosts()

                if use_deploy:
                    await add_deploy(state, run_once_deploy)
                else:
                    await add_op(state, run_once_operation, _run_once=True)

                assert len(state.ops[first]) == 1
                assert state.ops[second] == {}

                await run_ops(state)

                assert first.connector.executed_commands.count("echo once") == 1
                assert second.connector.executed_commands == []

    async def test_concurrent_independent_states(self):
        states = [
            State(
                Inventory(
                    ([f"@fake/{name}"], {}),
                    override_data={"fake_delay": 0.001, "fake_delay_jitter": 0.0},
                ),
                Config(),
            )
            for name in ("first", "second")
        ]
        seen = []

        @operation()
        def check_context():
            expected_state = context.host.state
            assert context.ctx_state.get() is expected_state
            assert context.ctx_inventory.get() is expected_state.inventory
            context.host.get_fact(Command, "echo ready")
            assert context.ctx_state.get() is expected_state
            assert context.ctx_inventory.get() is expected_state.inventory
            seen.append(context.host.name)
            yield StringCommand("echo done")

        async def prepare_and_run(state):
            with context.ctx_inventory.use(state.inventory):
                await connect_all(state)
                await add_op(state, check_context)
                await run_ops(state)

        original_state = context.ctx_state.get()
        original_inventory = context.ctx_inventory.get()
        await asyncio.gather(*(prepare_and_run(state) for state in states))

        assert seen.count("@fake/first") == 2
        assert seen.count("@fake/second") == 2
        assert context.ctx_state.get() is original_state
        assert context.ctx_inventory.get() is original_inventory
        for state in states:
            host = next(iter(state.inventory))
            assert len(state.ops[host]) == 1
            assert state.results[host].success_ops == 1
