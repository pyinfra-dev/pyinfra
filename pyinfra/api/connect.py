# pyinfra
# File: pyinfra/api/connect.py
# Desc: handle connecting to the inventory

import gevent
import six


def connect_all(state, progress=None):
    '''
    Connect to all the configured servers in parallel. Reads/writes state.inventory.

    Args:
        state (``pyinfra.api.State`` obj): the state containing an inventory to connect to
    '''

    greenlets = {}

    # Don't connect to anything within our (top level, --limit) limit
    hosts = [
        host for host in state.inventory
        if not isinstance(state.limit_hosts, list)
        or host in state.limit_hosts
    ]

    for host in hosts:
        greenlets[host] = state.pool.spawn(host.connect, state)

    # Wait for all the connections to complete
    for client in gevent.iwait(greenlets.values()):
        # Trigger CLI progress if provided
        if progress:
            progress()

    # Get/set the results
    failed_hosts = set()

    for host, greenlet in six.iteritems(greenlets):
        client = greenlet.get()

        if client:
            state.activate_host(host)
        else:
            failed_hosts.add(host)

    # Remove those that failed, triggering FAIL_PERCENT check
    state.fail_hosts(failed_hosts, activated_count=len(hosts))
