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

    for host in state.inventory:


    # Wait for all the connections to complete
    for _ in gevent.iwait(greenlets.values()):
        # Trigger CLI progress if provided
        if progress:
            progress()

    # Get/set the results
    failed_hosts = set()
    connected_host_names = set()

    for name, greenlet in six.iteritems(greenlets):
        client = greenlet.get()

        if not client:
            failed_hosts.add(name)
        else:
            connected_host_names.add(name)

    # Add connected hosts to inventory
    state.connected_host_names = connected_host_names

    # Add all the hosts as active
    state.active_host_names = set(greenlets.keys())

    # Remove those that failed, triggering FAIL_PERCENT check
    state.fail_hosts(failed_hosts)
