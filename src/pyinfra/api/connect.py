import asyncio
from typing import TYPE_CHECKING, Any, Callable

from pyinfra.progress import progress_spinner
from pyinfra.api.state import StateStage

if TYPE_CHECKING:
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


async def connect_all_async(state: "State") -> None:
    """
    Connect to all configured servers in parallel. Reads/writes ``state.inventory``.
    """

    if state.current_stage < StateStage.Connect:
        state.set_stage(StateStage.Connect)

    hosts = [host for host in state.inventory if state.is_host_in_limit(host)]

    if not hosts:
        return

    task_to_host = [
        (asyncio.create_task(state.run_in_executor(host.connect)), host) for host in hosts
    ]

    exceptions: list[tuple["Host", BaseException]] = []

    with progress_spinner(hosts) as progress:

        def _make_progress_callback(target_host: "Host") -> Callable[[asyncio.Future[Any]], None]:
            def _callback(_task: asyncio.Future[Any]) -> None:
                progress(target_host)

            return _callback

        for task, host in task_to_host:
            task.add_done_callback(_make_progress_callback(host))

        results = await asyncio.gather(*(task for task, _ in task_to_host), return_exceptions=True)

    for (task, host), result in zip(task_to_host, results, strict=True):
        if isinstance(result, BaseException):
            exceptions.append((host, result))

    failed_hosts = set()

    for host in hosts:
        if host.connected:
            state.activate_host(host)
        else:
            failed_hosts.add(host)

    state.fail_hosts(failed_hosts, activated_count=len(hosts))

    if exceptions:
        raise exceptions[0][1]


async def disconnect_all_async(state: "State") -> None:
    """Disconnect from all configured servers in parallel."""

    if state.current_stage < StateStage.Disconnect:
        state.set_stage(StateStage.Disconnect)

    hosts = list(state.activated_hosts)

    if not hosts:
        return

    task_to_host = [
        (asyncio.create_task(state.run_in_executor(host.disconnect)), host) for host in hosts
    ]

    exceptions: list[tuple["Host", BaseException]] = []

    with progress_spinner(hosts) as progress:

        def _make_progress_callback(target_host: "Host") -> Callable[[asyncio.Future[Any]], None]:
            def _callback(_task: asyncio.Future[Any]) -> None:
                progress(target_host)

            return _callback

        for task, host in task_to_host:
            task.add_done_callback(_make_progress_callback(host))

        results = await asyncio.gather(*(task for task, _ in task_to_host), return_exceptions=True)

    for (task, host), result in zip(task_to_host, results, strict=True):
        if isinstance(result, BaseException):
            exceptions.append((host, result))

    if exceptions:
        raise exceptions[0][1]


def connect_all(state: "State") -> None:
    try:
        asyncio.run(connect_all_async(state))
    except RuntimeError as exc:
        if "already running" in str(exc):
            raise RuntimeError(
                "connect_all cannot be called while an asyncio event loop is running. "
                "Use connect_all_async instead.",
            ) from exc
        raise


def disconnect_all(state: "State") -> None:
    try:
        asyncio.run(disconnect_all_async(state))
    except RuntimeError as exc:
        if "already running" in str(exc):
            raise RuntimeError(
                "disconnect_all cannot be called while an asyncio event loop is running. "
                "Use disconnect_all_async instead.",
            ) from exc
        raise
