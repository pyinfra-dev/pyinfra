from typing import TYPE_CHECKING

import gevent

from pyinfra.progress import progress_spinner

if TYPE_CHECKING:
    from pyinfra.api.state import State


def connect_all(state: "State"):
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

    greenlet_to_host = {state.pool.spawn(host.connect): host for host in hosts}

    with progress_spinner(greenlet_to_host.values()) as progress:
        for greenlet in gevent.iwait(greenlet_to_host.keys()):
            host = greenlet_to_host[greenlet]
            progress(host)

    # Get/set the results
    failed_hosts = set()

    for greenlet, host in greenlet_to_host.items():
        # Raise any unexpected exception
        greenlet.get()

        if host.connection:
            state.activate_host(host)
        else:
            failed_hosts.add(host)

    # Remove those that failed, triggering FAIL_PERCENT check
    state.fail_hosts(failed_hosts, activated_count=len(hosts))


def disconnect_all(state: "State"):
    for host in state.activated_hosts:  # only hosts we connected to please!
        host.disconnect()  # normally a noop
