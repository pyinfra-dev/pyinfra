"""
Bridges pyinfra's synchronous operation, fact and deploy code onto asyncio
without threads.

Per-host work runs inside a greenlet started by ``async_def``. When that sync
code reaches an I/O point inside a connector it hands a coroutine back to the
event loop with ``awaitlet`` and is resumed with the result once it completes.
``async_def`` and ``awaitlet`` are adapted from the MIT licensed ``awaitlet``
package, which is the mechanism SQLAlchemy uses for its asyncio support.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncGenerator, Awaitable, Callable, Coroutine, Generator, Iterable
from typing import Any, TypeVar, cast

from greenlet import getcurrent, greenlet

T = TypeVar("T")
H = TypeVar("H")

_GREENLET_MARKER = "__pyinfra_greenlet__"


class NoGreenletContext(RuntimeError):
    pass


class _AsyncIoGreenlet(greenlet):
    __pyinfra_greenlet__ = True

    def __init__(self, fn: Callable[..., Any], driver: greenlet):
        greenlet.__init__(self, fn, driver)
        # Share the driving task's contextvars context so ``pyinfra.host`` and
        # friends resolve inside the greenlet.
        self.gr_context = driver.gr_context


def in_greenlet() -> bool:
    return getattr(getcurrent(), _GREENLET_MARKER, False)


def awaitlet(awaitable: Awaitable[T]) -> T:
    """
    Await ``awaitable`` from synchronous code running inside an ``async_def``
    greenlet, returning its result.
    """
    current = getcurrent()
    if not getattr(current, _GREENLET_MARKER, False):
        if asyncio.iscoroutine(awaitable):
            awaitable.close()
        raise NoGreenletContext(
            "Cannot call blocking pyinfra APIs from async code outside of a pyinfra "
            "greenlet, use the async API (eg `await get_facts(...)`) instead.",
        )
    return current.parent.switch(awaitable)


async def async_def(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Run the synchronous ``fn`` in a new greenlet, servicing any ``awaitlet``
    calls it makes on the current event loop.
    """
    context = _AsyncIoGreenlet(fn, getcurrent())
    result = context.switch(*args, **kwargs)
    while not context.dead:
        try:
            value = await result
        except BaseException:
            result = context.throw(*sys.exc_info())
        else:
            result = context.switch(value)
    return result


async def _wait_for_future(future: asyncio.Future) -> None:
    await asyncio.wait([future])


def run_coroutine(coro: Coroutine[Any, Any, T]) -> T:
    """
    Drive ``coro`` to completion inside the current greenlet, so both ``await``
    and the synchronous pyinfra APIs work within it. This mirrors the asyncio
    task step loop: every future the coroutine awaits is handed to the event
    loop via ``awaitlet`` and the coroutine is resumed once it completes.
    """
    if not in_greenlet():
        raise NoGreenletContext("run_coroutine must be called from inside a pyinfra greenlet")

    send_value: Any = None
    throw_exc: BaseException | None = None

    while True:
        try:
            if throw_exc is not None:
                yielded = coro.throw(throw_exc)
            else:
                yielded = coro.send(send_value)
        except StopIteration as e:
            return e.value

        send_value = None
        throw_exc = None

        try:
            if yielded is None:
                awaitlet(asyncio.sleep(0))
            elif asyncio.isfuture(yielded):
                if yielded.get_loop() is not asyncio.get_running_loop():
                    raise RuntimeError(f"Future {yielded!r} belongs to a different event loop")
                # Acknowledge the yield exactly as Task.__step does: Future.__await__ sets
                # the flag before every yield and nothing reads it again, so no reset needed.
                yielded._asyncio_future_blocking = False
                awaitlet(_wait_for_future(yielded))
            else:
                throw_exc = RuntimeError(f"Coroutine yielded an unexpected value: {yielded!r}")
        except BaseException as e:
            if yielded is not None:
                yielded.cancel()
            throw_exc = e


def _iterate_async_generator(agen: AsyncGenerator[T, None]) -> Generator[T, None, None]:
    try:
        while True:
            try:
                yield run_coroutine(agen.__anext__())  # type: ignore[arg-type]
            except StopAsyncIteration:
                return
    finally:
        run_coroutine(agen.aclose())  # type: ignore[arg-type]


def iterate_async_generator(agen: AsyncGenerator[T, None]) -> Generator[T, None, None]:
    """
    Expose an async generator as a plain generator, running its body inside
    the current greenlet. Outside of a greenlet (eg direct calls from tests)
    the generator is consumed eagerly on a temporary event loop.
    """
    if in_greenlet():
        yield from _iterate_async_generator(agen)
    else:
        yield from asyncio.run(async_def(lambda: list(_iterate_async_generator(agen))))


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run ``coro`` from synchronous code: via ``awaitlet`` when inside a pyinfra
    greenlet, otherwise on a fresh event loop. The latter supports connector
    code called outside of a deploy, eg inventory generation from a plain script.
    """
    if in_greenlet():
        return awaitlet(coro)
    return asyncio.run(coro)


def run_with_timeout(fn: Callable[[], T], timeout: float | None) -> T:
    """
    Run synchronous ``fn`` inside a nested greenlet, cancelling it (at its next
    I/O point) if ``timeout`` seconds elapse.
    """
    if not timeout:
        return fn()

    async def run() -> T:
        try:
            return await asyncio.wait_for(async_def(fn), timeout)
        except asyncio.TimeoutError:
            raise TimeoutError()

    return awaitlet(run())


async def run_for_hosts(
    hosts: Iterable[H],
    fn: Callable[..., T],
    *args: Any,
    parallel: int | None = None,
    progress: Callable[[H], Any] | None = None,
    **kwargs: Any,
) -> dict[H, T]:
    """
    Run synchronous ``fn(host, *args, **kwargs)`` for every host concurrently,
    each in its own task and greenlet. All hosts run to completion; the first
    exception raised (in host order) is then re-raised.
    """
    hosts = list(hosts)
    semaphore = asyncio.Semaphore(parallel) if parallel else None

    async def run_host(host: H) -> T:
        try:
            if semaphore is None:
                return await async_def(fn, host, *args, **kwargs)
            async with semaphore:
                return await async_def(fn, host, *args, **kwargs)
        finally:
            if progress is not None:
                progress(host)

    results = await asyncio.gather(
        *(run_host(host) for host in hosts),
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, BaseException):
            raise result

    return dict(zip(hosts, cast(list[T], results)))
