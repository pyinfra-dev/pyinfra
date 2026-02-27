from __future__ import annotations

import asyncio

from pyinfra.api import Config, State, deploy
from pyinfra.api.state import StateStage
from pyinfra.async_context import AsyncContext, AsyncHostContext
from pyinfra.context import ctx_state
from pyinfra.facts.server import Command
from pyinfra.operations import files, server

from .util import make_inventory


def test_async_context_operation(fake_asyncssh):
    async def _run():
        inventory = make_inventory()
        state = State(inventory, Config())

        async with AsyncContext(state):
            results = await server.shell("echo async-context")

            assert set(results.keys()) == {
                inventory.get_host("somehost"),
                inventory.get_host("anotherhost"),
            }
            assert all(meta is not None for meta in results.values())
            assert state.current_stage == StateStage.Execute

            for connection in fake_asyncssh.values():
                assert any("echo async-context" in command for command in connection.commands_run)

        assert state.current_stage == StateStage.Disconnect
        for connection in fake_asyncssh.values():
            assert connection._closed is True

    asyncio.run(_run())


def test_async_context_fact(fake_asyncssh):
    async def _run():
        inventory = make_inventory()
        state = State(inventory, Config())

        async with AsyncContext(state):
            for connection in fake_asyncssh.values():
                connection.command_results["echo fact-value"] = {
                    "stdout": "value\n",
                    "stderr": "",
                    "exit_status": 0,
                }

            gathered = {}
            for hostname in ("somehost", "anotherhost"):
                host = inventory.get_host(hostname)
                gathered[host] = await host.get_fact(Command, "echo fact-value")

            assert set(gathered.keys()) == {
                inventory.get_host("somehost"),
                inventory.get_host("anotherhost"),
            }

            for value in gathered.values():
                assert value == "value"

        assert state.current_stage == StateStage.Disconnect
        for connection in fake_asyncssh.values():
            assert connection._closed is True

    asyncio.run(_run())


def test_async_context_hosts_subset(fake_asyncssh):
    async def _run():
        inventory = make_inventory()
        state = State(inventory, Config())

        specific = inventory.get_host("somehost")
        async with AsyncContext(state, hosts=[specific]):
            await server.shell("echo subset")

            assert any(
                "echo subset" in command for command in fake_asyncssh["somehost"].commands_run
            )
            assert "anotherhost" not in fake_asyncssh

        assert state.current_stage == StateStage.Disconnect
        assert fake_asyncssh["somehost"]._closed is True

    asyncio.run(_run())


def test_async_context_preserves_state_in_executor(fake_asyncssh, tmp_path):
    async def _run():
        inventory = make_inventory()
        state = State(inventory, Config())

        local_file = tmp_path / "async-context.txt"
        local_file.write_text("async context test")

        async with AsyncContext(state):
            results = await files.put(src=str(local_file), dest="/async-context.txt")

            assert set(results.keys()) == {
                inventory.get_host("somehost"),
                inventory.get_host("anotherhost"),
            }

            with ctx_state.use(state):
                state_in_executor = await state.run_in_executor(ctx_state.get)
                assert state_in_executor is state

                config_in_executor = await state.run_in_executor(lambda: ctx_state.get().config)
                assert config_in_executor is state.config

    asyncio.run(_run())


def test_async_context_run_deploy(fake_asyncssh):
    async def _run():
        inventory = make_inventory()
        state = State(inventory, Config())

        @deploy("Async context deploy")
        def sample_deploy():
            server.shell(name="Deploy op", commands="echo async-context-deploy")

        async with AsyncContext(state):
            await sample_deploy()

            for hostname, connection in fake_asyncssh.items():
                assert hostname in {"somehost", "anotherhost"}
                assert any(
                    "echo async-context-deploy" in command for command in connection.commands_run
                )

        fake_asyncssh.clear()

        async with AsyncContext(state, hosts=[inventory.get_host("somehost")]):
            await sample_deploy(hosts=[inventory.get_host("somehost")])

            assert set(fake_asyncssh.keys()) == {"somehost"}
            assert any(
                "echo async-context-deploy" in command
                for command in fake_asyncssh["somehost"].commands_run
            )

        assert all(connection._closed for connection in fake_asyncssh.values())
        fake_asyncssh.clear()

    asyncio.run(_run())


def test_async_host_context_limits_to_single_host(fake_asyncssh):
    async def _run():
        inventory = make_inventory()
        state = State(inventory, Config())

        async with AsyncHostContext(state, "somehost"):
            results = await server.shell("echo host-context")

            somehost = inventory.get_host("somehost")
            assert set(results.keys()) == {somehost}
            assert set(fake_asyncssh.keys()) == {"somehost"}

            fake_asyncssh["somehost"].command_results["echo async-host-fact"] = {
                "stdout": "value\n",
                "stderr": "",
                "exit_status": 0,
            }

            fact_value = await somehost.get_fact(Command, "echo async-host-fact")
            assert fact_value == "value"

            @deploy("Async host deploy")
            def sample_host_deploy():
                server.shell(name="Host deploy op", commands="echo async-host-deploy")

            await sample_host_deploy()
            assert any(
                "echo async-host-deploy" in command
                for command in fake_asyncssh["somehost"].commands_run
            )

        assert fake_asyncssh["somehost"]._closed is True
        assert "anotherhost" not in fake_asyncssh

    asyncio.run(_run())


def test_async_host_context_accepts_host_object(fake_asyncssh):
    async def _run():
        inventory = make_inventory()
        state = State(inventory, Config())

        host_obj = inventory.get_host("somehost")
        async with AsyncHostContext(state, host_obj):
            await server.shell("echo host-object")

            fake_asyncssh["somehost"].command_results["echo host-object-fact"] = {
                "stdout": "value\n",
                "stderr": "",
                "exit_status": 0,
            }

            value = await host_obj.get_fact(Command, "echo host-object-fact")
            assert value == "value"

            @deploy("Async host object deploy")
            def sample_host_object_deploy():
                server.shell(name="Host object deploy", commands="echo async-host-object")

            await sample_host_object_deploy()

        assert set(fake_asyncssh.keys()) == {"somehost"}
        assert any(
            "echo async-host-object" in command
            for command in fake_asyncssh["somehost"].commands_run
        )

    asyncio.run(_run())
