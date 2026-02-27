from __future__ import annotations

import asyncio
from contextlib import ExitStack
from contextvars import Token
from functools import partial
from typing import Any, Iterable, Mapping

from typing_extensions import Protocol

from pyinfra.api.host import Host
from pyinfra.api.operation import (
    OperationMeta,
    execute_immediately,
    push_async_context,
    reset_async_context,
    suspend_async_context,
)
from pyinfra.api.state import State, StateStage
from pyinfra.context import ctx_config, ctx_host, ctx_inventory, ctx_state


class SupportsOperation(Protocol):
    def __call__(self, *args, **kwargs) -> OperationMeta:  # pragma: no cover - Protocol stub
        ...


class _AsyncOperationAwaitable:
    def __init__(
        self,
        context: "AsyncContext",
        operation: SupportsOperation,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        hosts_override: Iterable[Host | str] | None,
    ) -> None:
        self._context = context
        self._operation = operation
        self._args = args
        self._kwargs = kwargs
        self._hosts_override = hosts_override

    def __await__(self):
        return self._run().__await__()

    async def _run(self) -> Mapping[Host, OperationMeta]:
        suspend_token = suspend_async_context()
        try:
            return await self._context.run_operation(
                self._operation,
                *self._args,
                hosts=self._hosts_override,
                **self._kwargs,
            )
        finally:
            reset_async_context(suspend_token)


class _AsyncDeployAwaitable:
    def __init__(
        self,
        context: "AsyncContext",
        deploy_fn,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        hosts_override: Iterable[Host | str] | None,
    ) -> None:
        self._context = context
        self._deploy_fn = deploy_fn
        self._args = args
        self._kwargs = kwargs
        self._hosts_override = hosts_override

    def __await__(self):
        return self._run().__await__()

    async def _run(self) -> None:
        suspend_token = suspend_async_context()
        try:
            await self._context.run_deploy(
                self._deploy_fn,
                *self._args,
                hosts=self._hosts_override,
                **self._kwargs,
            )
        finally:
            reset_async_context(suspend_token)


class _AsyncFactAwaitable:
    def __init__(
        self,
        context: "AsyncContext",
        host: Host,
        fact_cls,
        fact_args: tuple[Any, ...],
        fact_kwargs: dict[str, Any],
    ) -> None:
        self._context = context
        self._host = host
        self._fact_cls = fact_cls
        self._fact_args = fact_args
        self._fact_kwargs = fact_kwargs

    def __await__(self):
        return self._run().__await__()

    async def _run(self) -> Any:
        suspend_token = suspend_async_context()
        try:
            await self._context._ensure_hosts_connected([self._host])
            return await self._context.state.run_in_executor(
                partial(
                    self._context._fetch_fact,
                    self._host,
                    self._fact_cls,
                    self._fact_args,
                    self._fact_kwargs,
                )
            )
        finally:
            reset_async_context(suspend_token)


class AsyncContext:
    """Async helper for running individual operations or facts against hosts."""

    def __init__(
        self,
        state: State,
        hosts: Iterable[Host | str] | None = None,
    ) -> None:
        self.state = state
        self._default_hosts = self._normalise_hosts(hosts)
        self._managed_hosts: set[Host] = set()
        self._auto_manage_connections = False
        self._in_context = False
        self._context_token: Token | None = None

    def _normalise_hosts(self, hosts: Iterable[Host | str] | None) -> list[Host]:
        if hosts is None:
            return list(self.state.inventory.iter_active_hosts()) or list(self.state.inventory)

        normalised: list[Host] = []
        for host in hosts:
            if isinstance(host, Host):
                normalised.append(host)
            else:
                resolved = self.state.inventory.get_host(host)
                if resolved is None:
                    raise ValueError(f"Unknown host: {host}")
                normalised.append(resolved)
        return normalised

    def _with_context(self, host: Host):
        stack = ExitStack()
        stack.enter_context(ctx_state.use(self.state))
        stack.enter_context(ctx_inventory.use(self.state.inventory))
        stack.enter_context(ctx_config.use(self.state.config.copy()))
        stack.enter_context(ctx_host.use(host))
        return stack

    async def __aenter__(self) -> "AsyncContext":
        if self._in_context:
            raise RuntimeError("AsyncContext is already in use as a context manager")

        self._auto_manage_connections = True
        self._in_context = True

        if self.state.current_stage < StateStage.Connect:
            self.state.set_stage(StateStage.Connect)

        try:
            await self._ensure_hosts_connected(self._default_hosts)
        except BaseException:
            # Ensure the context flags are reset if connection setup fails
            self._auto_manage_connections = False
            self._in_context = False
            raise

        self._context_token = push_async_context(self)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001 - async context protocol
        disconnect_error: BaseException | None = None

        try:
            if self._auto_manage_connections:
                try:
                    await self._disconnect_managed_hosts()
                except BaseException as exc_disconnect:
                    disconnect_error = exc_disconnect
        finally:
            self._auto_manage_connections = False
            self._in_context = False
            if self._context_token is not None:
                reset_async_context(self._context_token)
                self._context_token = None

        if self.state.current_stage < StateStage.Disconnect:
            self.state.set_stage(StateStage.Disconnect)

        if disconnect_error is not None and exc_type is None:
            raise disconnect_error

    def _call_wrapped_operation(
        self,
        operation: SupportsOperation,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> "_AsyncOperationAwaitable":
        op_kwargs = dict(kwargs)
        hosts_override = op_kwargs.pop("hosts", None)
        return _AsyncOperationAwaitable(self, operation, args, op_kwargs, hosts_override)

    def _call_wrapped_deploy(
        self,
        deploy_fn,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> _AsyncDeployAwaitable:
        deploy_kwargs = dict(kwargs)
        hosts_override = deploy_kwargs.pop("hosts", None)
        return _AsyncDeployAwaitable(self, deploy_fn, args, deploy_kwargs, hosts_override)

    def _call_wrapped_fact(
        self,
        host: Host,
        fact_cls,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> _AsyncFactAwaitable:
        fact_kwargs = dict(kwargs)
        return _AsyncFactAwaitable(self, host, fact_cls, args, fact_kwargs)

    async def _ensure_hosts_connected(self, hosts: Iterable[Host]) -> None:
        if not self._auto_manage_connections:
            return

        hosts_to_connect = [host for host in hosts if not host.connected]
        if not hosts_to_connect:
            return

        connect_tasks = [
            asyncio.create_task(host.connect_async(reason="async context", raise_exceptions=True))
            for host in hosts_to_connect
        ]

        results = await asyncio.gather(*connect_tasks, return_exceptions=True)

        successful_hosts: list[Host] = []
        errors: list[BaseException] = []

        for host, result in zip(hosts_to_connect, results):
            if isinstance(result, BaseException):
                errors.append(result)
            else:
                self._managed_hosts.add(host)
                successful_hosts.append(host)

        if errors:
            if successful_hosts:
                await self._disconnect_managed_hosts(successful_hosts)
            raise errors[0]

    async def _disconnect_managed_hosts(self, hosts: Iterable[Host] | None = None) -> None:
        targets = list(hosts) if hosts is not None else list(self._managed_hosts)
        if not targets:
            return

        disconnect_hosts: list[Host] = []
        disconnect_tasks = []

        for host in targets:
            if host.connected:
                disconnect_hosts.append(host)
                disconnect_tasks.append(asyncio.create_task(host.disconnect_async()))
            else:
                self._managed_hosts.discard(host)

        if disconnect_tasks:
            results = await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            errors: list[BaseException] = []
            for host, result in zip(disconnect_hosts, results):
                self._managed_hosts.discard(host)
                if isinstance(result, BaseException):
                    errors.append(result)
            if errors:
                raise errors[0]

        # Remove any hosts that were not connected (no task created) from management tracking
        for host in set(targets) - set(disconnect_hosts):
            self._managed_hosts.discard(host)

    async def run_operation(
        self,
        operation: SupportsOperation,
        *args,
        hosts: Iterable[Host | str] | None = None,
        **kwargs,
    ) -> Mapping[Host, OperationMeta]:
        """Execute an operation immediately for each host and await completion."""

        targets = self._normalise_hosts(hosts) if hosts is not None else self._default_hosts

        suspend_token = suspend_async_context()
        try:
            await self._ensure_hosts_connected(targets)

            results = {}
            for host in targets:
                op_meta = await self.state.run_in_executor(
                    partial(self._execute_operation, host, operation, args, kwargs)
                )
                results[host] = op_meta
            return results
        finally:
            reset_async_context(suspend_token)

    def _execute_operation(
        self,
        host: Host,
        operation: SupportsOperation,
        op_args: tuple[Any, ...],
        op_kwargs: dict[str, Any],
    ) -> OperationMeta:
        with self._with_context(host):
            if self.state.current_stage < StateStage.Prepare:
                self.state.set_stage(StateStage.Prepare)
            if self.state.current_stage < StateStage.Execute:
                self.state.set_stage(StateStage.Execute)
            elif self.state.current_stage > StateStage.Execute:
                self.state.current_stage = StateStage.Execute

            was_executing = self.state.is_executing
            if not was_executing:
                self.state.is_executing = True

            if host not in self.state.activated_hosts:
                self.state.activate_host(host)

            try:
                op_meta = operation(*op_args, **op_kwargs)

                if not op_meta.is_complete():
                    execute_immediately(self.state, host, op_meta._hash)

                return op_meta
            finally:
                if not was_executing:
                    self.state.is_executing = False

    async def get_fact(
        self,
        fact_cls,
        *fact_args,
        hosts: Iterable[Host | str] | None = None,
        **fact_kwargs,
    ) -> Mapping[Host, Any]:
        """Fetch a fact asynchronously for the selected hosts."""

        targets = self._normalise_hosts(hosts) if hosts is not None else self._default_hosts

        suspend_token = suspend_async_context()
        try:
            await self._ensure_hosts_connected(targets)

            results = {}
            for host in targets:
                value = await self.state.run_in_executor(
                    partial(self._fetch_fact, host, fact_cls, fact_args, fact_kwargs)
                )
                results[host] = value
            return results
        finally:
            reset_async_context(suspend_token)

    def _fetch_fact(
        self,
        host: Host,
        fact_cls,
        fact_args: tuple[Any, ...],
        fact_kwargs: dict[str, Any],
    ) -> Any:
        with self._with_context(host):
            return host.get_fact(fact_cls, *fact_args, **fact_kwargs)

    async def run_deploy(
        self,
        deploy_fn,
        *deploy_args,
        hosts: Iterable[Host | str] | None = None,
        **deploy_kwargs,
    ) -> None:
        """Execute a deploy coroutine immediately for the selected hosts."""

        targets = self._normalise_hosts(hosts) if hosts is not None else self._default_hosts

        suspend_token = suspend_async_context()
        try:
            await self._ensure_hosts_connected(targets)

            for host in targets:
                await self.state.run_in_executor(
                    partial(self._execute_deploy, host, deploy_fn, deploy_args, deploy_kwargs)
                )
        finally:
            reset_async_context(suspend_token)

    def _execute_deploy(
        self,
        host: Host,
        deploy_fn,
        deploy_args: tuple[Any, ...],
        deploy_kwargs: dict[str, Any],
    ) -> None:
        with self._with_context(host):
            if self.state.current_stage < StateStage.Prepare:
                self.state.set_stage(StateStage.Prepare)
            if self.state.current_stage < StateStage.Execute:
                self.state.set_stage(StateStage.Execute)
            elif self.state.current_stage > StateStage.Execute:
                self.state.current_stage = StateStage.Execute

            was_executing = self.state.is_executing
            if not was_executing:
                self.state.is_executing = True

            if host not in self.state.activated_hosts:
                self.state.activate_host(host)

            try:
                deploy_fn(*deploy_args, **deploy_kwargs)
            finally:
                if not was_executing:
                    self.state.is_executing = False


class AsyncHostContext:
    """Convenience wrapper around :class:`AsyncContext` for a single host."""

    def __init__(self, state: State, host: Host | str) -> None:
        self.state = state
        self._host_arg = host
        self.host: Host | None = None
        self._context: AsyncContext | None = None

    def _resolve_host(self) -> Host:
        if isinstance(self._host_arg, Host):
            return self._host_arg

        resolved = self.state.inventory.get_host(self._host_arg)
        if resolved is None:
            raise ValueError(f"Unknown host: {self._host_arg}")
        return resolved

    async def __aenter__(self) -> AsyncContext:
        self.host = self._resolve_host()
        self._context = AsyncContext(self.state, hosts=[self.host])
        return await self._context.__aenter__()

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001 - async context protocol
        if self._context is None:
            return
        await self._context.__aexit__(exc_type, exc, tb)
        self._context = None
