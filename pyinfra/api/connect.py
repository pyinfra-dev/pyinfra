import gevent
import six

from pyinfra.progress import progress_spinner


def connect_all(state):
    '''
    Connect to all the configured servers in parallel. Reads/writes state.inventory.

    Args:
        state (``pyinfra.api.State`` obj): the state containing an inventory to connect to
    '''

    hosts = [
        host for host in state.inventory
        if state.is_host_in_limit(host)  # these are the hosts to activate ("initially connect to")
    ]

    greenlet_to_host = {
        state.pool.spawn(host.connect): host
        for host in hosts
    }

    with progress_spinner(greenlet_to_host.values()) as progress:
        for greenlet in gevent.iwait(greenlet_to_host.keys()):
            host = greenlet_to_host[greenlet]
            progress(host)

    # Get/set the results
    failed_hosts = set()

    for greenlet, host in six.iteritems(greenlet_to_host):
        # Raise any unexpected exception
        greenlet.get()

        if host.connection:
            state.activate_host(host)
        else:
            failed_hosts.add(host)

    # Remove those that failed, triggering FAIL_PERCENT check
    state.fail_hosts(failed_hosts, activated_count=len(hosts))


def disconnect_all(state):
    for host in state.activated_hosts:  # only hosts we connected to please!
        host.disconnect()  # normally a noop
