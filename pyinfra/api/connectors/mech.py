import json

from os import path
from threading import Thread

from six.moves.queue import Queue

from pyinfra import local, logger
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import memoize
from pyinfra.progress import progress_spinner


def _get_mech_ssh_config(queue, progress, target):
    logger.debug('Loading SSH config for {0}'.format(target))

    # Note: We have to work-around the fact that "mech ssh-config somehost"
    # does not return the correct "Host" value. When "mech" fixes this
    # issue we can simply this code.
    lines = local.shell(
        'mech ssh-config {0}'.format(target),
        splitlines=True,
    )

    newlines = []
    for line in lines:
        if line.startswith('Host '):
            newlines.append('Host ' + target)
        else:
            newlines.append(line)

    queue.put(newlines)

    progress(target)


@memoize
def get_mech_config(limit=None):
    logger.info('Getting Mech config...')

    if limit and not isinstance(limit, (list, tuple)):
        limit = [limit]

    # Note: There is no "--machine-readable" option to 'mech status'
    with progress_spinner({'mech ls'}) as progress:
        output = local.shell(
            'mech ls',
            splitlines=True,
        )
        progress('mech ls')

    targets = []

    for line in output:

        address = ''

        data = line.split()
        target = data[0]

        if len(data) == 5:
            address = data[1]

        # Skip anything not in the limit
        if limit is not None and target not in limit:
            continue

        # For each vm that has an address, fetch it's SSH config in a thread
        if address != '' and address[0].isdigit():
            targets.append(target)

    threads = []
    config_queue = Queue()

    with progress_spinner(targets) as progress:
        for target in targets:
            thread = Thread(
                target=_get_mech_ssh_config,
                args=(config_queue, progress, target),
            )
            threads.append(thread)
            thread.start()

    for thread in threads:
        thread.join()

    queue_items = list(config_queue.queue)

    lines = []
    for output in queue_items:
        lines.extend(output)

    return lines


@memoize
def get_mech_options():
    if path.exists('@mech.json'):
        with open('@mech.json', 'r') as f:
            return json.loads(f.read())
    return {}


def _make_name_data(host):
    mech_options = get_mech_options()
    mech_host = host['Host']

    data = {
        'ssh_hostname': host['HostName'],
    }

    for config_key, data_key in (
        ('Port', 'ssh_port'),
        ('User', 'ssh_user'),
        ('IdentityFile', 'ssh_key'),
    ):
        if config_key in host:
            data[data_key] = host[config_key]

    # Update any configured JSON data
    if mech_host in mech_options.get('data', {}):
        data.update(mech_options['data'][mech_host])

    # Work out groups
    groups = mech_options.get('groups', {}).get(mech_host, [])

    if '@mech' not in groups:
        groups.append('@mech')

    return '@mech/{0}'.format(host['Host']), data, groups


def make_names_data(limit=None):
    mech_ssh_info = get_mech_config(limit)

    logger.debug('Got Mech SSH info: \n{0}'.format(mech_ssh_info))

    hosts = []
    current_host = None

    for line in mech_ssh_info:
        if not line:
            if current_host:
                hosts.append(_make_name_data(current_host))

            current_host = None
            continue

        key, value = line.strip().split(' ', 1)

        if key == 'Host':
            if current_host:
                hosts.append(_make_name_data(current_host))

            # Set the new host
            current_host = {
                key: value,
            }

        elif current_host:
            current_host[key] = value

        else:
            logger.debug('Extra Mech SSH key/value ({0}={1})'.format(
                key, value,
            ))

    if current_host:
        hosts.append(_make_name_data(current_host))

    if not hosts:
        raise InventoryError('No running Mech instances found!')

    return hosts
