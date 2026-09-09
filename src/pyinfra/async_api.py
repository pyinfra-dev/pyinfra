"""
Asyncio embedding API.

pyinfra's core is synchronous (gevent-based), which conflicts with an asyncio
event loop running in the same thread. This module runs all pyinfra work on a
dedicated worker thread so deploys can be driven from asyncio applications.

Note this does not gevent monkey-patch the process - doing so would break the
host asyncio loop - so pyinfra's own internal concurrency still applies within
the worker thread only.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from functools import partial
from typing import Any

from typing_extensions import Self

from pyinfra.api.host import Host
from pyinfra.api.operation import OperationMeta, execute_immediately
from pyinfra.api.state import State
from pyinfra.context import ctx_config, ctx_host, ctx_inventory, ctx_state


class AsyncPyinfra:
    """
    Run pyinfra operations and facts from asyncio code.

    All pyinfra calls are serialised onto a single worker thread because
    ``State`` and the gevent hub are bound to the thread that uses them.

    + state: the ``pyinfra.api.State`` to run against
    + host: default ``Host`` to target, may be overridden per call

    **Example:**

    .. code:: python

        async with AsyncPyinfra(state, host=host) as async_pyinfra:
            await async_pyinfra.connect()
            meta = await async_pyinfra.run_operation(server.shell, commands=["echo hi"])
            uptime = await async_pyinfra.get_fact(Uptime)
    """

    def __init__(self, state: State, host: Host | None = None) -> None:
        self.state = state
        self.host = host
        self._executor: ThreadPoolExecutor | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    async def close(self) -> None:
        executor, self._executor = self._executor, None
        if executor is not None:
            await asyncio.get_running_loop().run_in_executor(None, executor.shutdown)

    def _get_executor(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pyinfra-async")
        return self._executor

    def _get_host(self, host: Host | None) -> Host:
        host = host or self.host
        if host is None:
            raise ValueError("No host: pass one to `AsyncPyinfra()` or to the method call")
        return host

    def _enter_context(self, stack: ExitStack, host: Host | None) -> None:
        stack.enter_context(ctx_state.use(self.state))
        stack.enter_context(ctx_config.use(self.state.config))
        stack.enter_context(ctx_inventory.use(self.state.inventory))
        if host is not None:
            stack.enter_context(ctx_host.use(host))

    async def _run_in_worker(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._get_executor(), partial(func, *args, **kwargs))

    async def connect(self) -> None:
        def _connect() -> None:
            with ExitStack() as stack:
                if self.host is not None:
                    self._enter_context(stack, self.host)
                    self.host.connect(raise_exceptions=True)
                    self.state.activate_host(self.host)
                else:
                    self._enter_context(stack, None)
                    from pyinfra.api.connect import connect_all

                    connect_all(self.state)

        await self._run_in_worker(_connect)

    async def disconnect(self) -> None:
        def _disconnect() -> None:
            with ExitStack() as stack:
                if self.host is not None:
                    self._enter_context(stack, self.host)
                    self.host.disconnect()
                else:
                    self._enter_context(stack, None)
                    from pyinfra.api.connect import disconnect_all

                    disconnect_all(self.state)

        await self._run_in_worker(_disconnect)

    async def run_operation(
        self,
        operation: Callable[..., OperationMeta],
        *args: Any,
        host: Host | None = None,
        **kwargs: Any,
    ) -> OperationMeta:
        target = self._get_host(host)

        def _run() -> OperationMeta:
            with ExitStack() as stack:
                self._enter_context(stack, target)
                op_meta = operation(*args, **kwargs)
                if not op_meta.executed:
                    execute_immediately(self.state, target, op_meta._hash)
                return op_meta

        return await self._run_in_worker(_run)

    async def get_fact(
        self,
        fact_cls: Any,
        *args: Any,
        host: Host | None = None,
        **kwargs: Any,
    ) -> Any:
        target = self._get_host(host)

        def _get() -> Any:
            with ExitStack() as stack:
                self._enter_context(stack, target)
                return target.get_fact(fact_cls, *args, **kwargs)

        return await self._run_in_worker(_get)
