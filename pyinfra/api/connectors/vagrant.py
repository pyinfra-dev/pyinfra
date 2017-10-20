import json

from os import path
from threading import Thread

from six.moves.queue import Queue

from pyinfra import local, logger

VAGRANT_CONFIG = None
VAGRANT_GROUPS = None


def _get_vagrant_ssh_config(queue, target):
    logger.debug('Loading SSH config for {0}'.format(target))

    queue.put(local.shell(
        'vagrant ssh-config {0}'.format(target),
        splitlines=True,
    ))


def _get_vagrant_config(limit=None):
    if limit and not isinstance(limit, list):
        limit = [limit]

    output = local.shell(
        'vagrant status --machine-readable',
        splitlines=True,
    )

    config_queue = Queue()
    threads = []

    for line in output:
        _, target, type_, data = line.split(',', 3)

        # Skip anything not in the limit
        if limit is not None and target not in limit:
            continue

        # For each running container - fetch it's SSH config in a thread - this
        # is because Vagrant *really* slow to run each command.
        if type_ == 'state' and data == 'running':
            thread = Thread(
                target=_get_vagrant_ssh_config,
                args=(config_queue, target),
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


def get_vagrant_config(limit=None):
    global VAGRANT_CONFIG

    if VAGRANT_CONFIG is None:
        logger.info('Getting vagrant config...')

        VAGRANT_CONFIG = _get_vagrant_config(limit=limit)

    return VAGRANT_CONFIG


def get_vagrant_groups():
    global VAGRANT_GROUPS

    if VAGRANT_GROUPS is None:
        if path.exists('@vagrant.json'):
            with open('@vagrant.json', 'r') as f:
                VAGRANT_GROUPS = json.loads(f.read()).get('groups', {})
        else:
            VAGRANT_GROUPS = {}

    return VAGRANT_GROUPS


def _make_name_data(host):
    host_to_group = get_vagrant_groups()

    # Build data
    data = {
        'ssh_hostname': host['HostName'],
        'ssh_port': host['Port'],
        'ssh_user': host['User'],
        'ssh_key': host['IdentityFile'],
    }

    # Work out groups
    groups = host_to_group.get(host['Host'], [])

    if '@vagrant' not in groups:
        groups.append('@vagrant')

    return '@vagrant/{0}'.format(host['Host']), data, groups


def make_names_data(limit=None):
    vagrant_ssh_info = get_vagrant_config(limit)

    logger.debug('Got Vagrant SSH info: \n{0}'.format(vagrant_ssh_info))

    current_host = None

    for line in vagrant_ssh_info:
        # Vagrant outputs an empty line between each host
        if not line:
            # yield any previous host
            if current_host:
                yield _make_name_data(current_host)

            current_host = None
            continue

        key, value = line.split(' ', 1)

        if key == 'Host':
            # yield any previous host
            if current_host:
                yield _make_name_data(current_host)

            # Set the new host
            current_host = {
                key: value,
            }

        elif current_host:
            current_host[key] = value

        else:
            logger.debug('Extra Vagrant SSH key/value ({0}={1})'.format(
                key, value,
            ))

    # yield any leftover host
    if current_host:
        yield _make_name_data(current_host)
