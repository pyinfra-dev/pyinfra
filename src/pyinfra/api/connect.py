from typing import TYPE_CHECKING

from pyinfra.progress import progress_spinner

from .concurrency import run_for_hosts

if TYPE_CHECKING:
    from pyinfra.api.state import State


async def connect_all(state: "State") -> None:
    """
    Connect to all the configured servers in parallel. Reads/writes state.inventory.

    Args:
        state (``pyinfra.api.State`` obj): the state containing an inventory to connect to
    """

    hosts = [
        host
        for host in state.inventory
        if state.is_host_in_limit(host)  # these are the hosts to activate ("initially connect to")
    ]

    with progress_spinner(hosts) as progress:
        await run_for_hosts(
            hosts,
            lambda host: host.connect(),
            parallel=state.config.PARALLEL,
            progress=progress,
        )

    # Get/set the results
    failed_hosts = set()

    for host in hosts:
        if host.connected:
            state.activate_host(host)
        else:
            failed_hosts.add(host)

    # Remove those that failed, triggering FAIL_PERCENT check
    state.fail_hosts(failed_hosts, activated_count=len(hosts))


async def disconnect_all(state: "State") -> None:
    """
    Disconnect from all of the configured servers in parallel. Reads/writes state.inventory.

    Args:
        state (``pyinfra.api.State`` obj): the state containing an inventory to connect to
    """
    hosts = list(state.activated_hosts)  # only hosts we connected to please!

    with progress_spinner(hosts) as progress:
        await run_for_hosts(
            hosts,
            lambda host: host.disconnect(),
            parallel=state.config.PARALLEL,
            progress=progress,
        )
