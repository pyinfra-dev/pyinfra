import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent
from unittest import TestCase


def run_async_script(script: str) -> subprocess.CompletedProcess:
    # The pytest process itself is gevent monkey-patched (pyinfra_testing
    # imports pyinfra_cli), which conflicts with asyncio, so exercise the
    # async API the way it is meant to be used: in a clean subprocess.
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(dedent(script))
        path = Path(f.name)

    try:
        return subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        path.unlink()


class TestAsyncPyinfra(TestCase):
    def test_connect_run_operation_get_fact(self):
        result = run_async_script(
            """
            import asyncio

            from pyinfra.api import Config, Inventory, State
            from pyinfra.async_api import AsyncPyinfra
            from pyinfra.facts.server import Os
            from pyinfra.operations import server

            async def main():
                state = State(Inventory((["@local"], {})), Config())
                host = state.inventory.get_host("@local")
                async with AsyncPyinfra(state, host=host) as async_pyinfra:
                    await async_pyinfra.connect()
                    assert host.connected

                    op_meta = await async_pyinfra.run_operation(
                        server.shell,
                        commands=["echo hello"],
                    )
                    assert op_meta.executed
                    assert op_meta.did_change()

                    os_name = await async_pyinfra.get_fact(Os)
                    assert os_name
                    print("OS:", os_name)

                    await async_pyinfra.disconnect()
                print("ASYNC_PYINFRA_OK")

            asyncio.run(main())
            """
        )
        assert result.returncode == 0, result.stderr
        assert "ASYNC_PYINFRA_OK" in result.stdout

    def test_host_override_and_concurrent_gather(self):
        result = run_async_script(
            """
            import asyncio

            from pyinfra.api import Config, Inventory, State
            from pyinfra.async_api import AsyncPyinfra
            from pyinfra.facts.server import Home, Os

            async def main():
                state = State(Inventory((["@local"], {})), Config())
                host = state.inventory.get_host("@local")
                async with AsyncPyinfra(state) as async_pyinfra:
                    await async_pyinfra.connect()
                    os_name, home = await asyncio.gather(
                        async_pyinfra.get_fact(Os, host=host),
                        async_pyinfra.get_fact(Home, host=host),
                    )
                    assert os_name and home
                print("ASYNC_PYINFRA_OK")

            asyncio.run(main())
            """
        )
        assert result.returncode == 0, result.stderr
        assert "ASYNC_PYINFRA_OK" in result.stdout

    def test_no_host_raises(self):
        result = run_async_script(
            """
            import asyncio

            from pyinfra.api import Config, Inventory, State
            from pyinfra.async_api import AsyncPyinfra
            from pyinfra.facts.server import Os

            async def main():
                state = State(Inventory((["@local"], {})), Config())
                async_pyinfra = AsyncPyinfra(state)
                try:
                    await async_pyinfra.get_fact(Os)
                except ValueError:
                    print("ASYNC_PYINFRA_OK")
                else:
                    raise AssertionError("expected ValueError")

            asyncio.run(main())
            """
        )
        assert result.returncode == 0, result.stderr
        assert "ASYNC_PYINFRA_OK" in result.stdout

    def test_failing_operation_raises(self):
        result = run_async_script(
            """
            import asyncio

            from pyinfra.api import Config, Inventory, State
            from pyinfra.api.exceptions import NestedOperationError
            from pyinfra.async_api import AsyncPyinfra
            from pyinfra.operations import server

            async def main():
                state = State(Inventory((["@local"], {})), Config())
                host = state.inventory.get_host("@local")
                async with AsyncPyinfra(state, host=host) as async_pyinfra:
                    await async_pyinfra.connect()
                    try:
                        await async_pyinfra.run_operation(
                            server.shell,
                            commands=["exit 1"],
                        )
                    except NestedOperationError:
                        print("ASYNC_PYINFRA_OK")
                    else:
                        raise AssertionError("expected NestedOperationError")

            asyncio.run(main())
            """
        )
        assert result.returncode == 0, result.stderr
        assert "ASYNC_PYINFRA_OK" in result.stdout

    def test_connect_disconnect_all_hosts(self):
        result = run_async_script(
            """
            import asyncio

            from pyinfra.api import Config, Inventory, State
            from pyinfra.async_api import AsyncPyinfra

            async def main():
                state = State(Inventory((["@local"], {})), Config())
                host = state.inventory.get_host("@local")
                async with AsyncPyinfra(state) as async_pyinfra:
                    await async_pyinfra.connect()
                    assert host.connected
                    assert host in state.active_hosts
                    await async_pyinfra.disconnect()
                    assert not host.connected
                print("ASYNC_PYINFRA_OK")

            asyncio.run(main())
            """
        )
        assert result.returncode == 0, result.stderr
        assert "ASYNC_PYINFRA_OK" in result.stdout

    def test_failed_connect_raises(self):
        result = run_async_script(
            """
            import asyncio

            from pyinfra.api import Config, Inventory, State
            from pyinfra.api.exceptions import ConnectError
            from pyinfra.async_api import AsyncPyinfra

            async def main():
                state = State(
                    Inventory(([("127.0.0.1", {"ssh_port": 1, "ssh_connect_retries": 1})], {})),
                    Config(),
                )
                host = state.inventory.get_host("127.0.0.1")
                async with AsyncPyinfra(state, host=host) as async_pyinfra:
                    try:
                        await async_pyinfra.connect()
                    except ConnectError:
                        pass
                    else:
                        raise AssertionError("expected ConnectError")
                    assert not host.connected
                    assert host not in state.active_hosts
                print("ASYNC_PYINFRA_OK")

            asyncio.run(main())
            """
        )
        assert result.returncode == 0, result.stderr
        assert "ASYNC_PYINFRA_OK" in result.stdout
