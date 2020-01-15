import re

from collections import defaultdict
from configparser import ConfigParser
from os import path

from pyinfra import logger
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import memoize


@memoize
def show_warning():
    logger.warning('The @ansible connector is in alpha!')


@memoize
def get_ansible_inventory(inventory_filename=None):
    if not inventory_filename:  # pragma: no cover
        raise InventoryError('No Ansible inventory filename provided!')

    if not path.exists(inventory_filename):
        raise InventoryError((
            'Could not find Ansible inventory file: {0}'
        ).format(inventory_filename))

    logger.info('Parsing Ansible inventory...')

    config = ConfigParser(
        delimiters=(' '),  # we only handle the hostnames for now
        allow_no_value=True,  # we don't by default have = values
        interpolation=None,  # remove any Python interpolation
    )
    config.read(inventory_filename)
    return config


def _parse_ansible_hosts(hosts):
    for host in hosts:
        expand_match = re.search(r'\[[0-9:]+\]', host)
        if expand_match:
            expand_string = host[expand_match.start():expand_match.end()]
            bits = expand_string[1:-1].split(':')  # remove the [] either side

            zfill = 0
            if bits[0].startswith('0'):
                zfill = len(bits[0])

            start, end = int(bits[0]), int(bits[1])
            step = int(bits[2]) if len(bits) > 2 else 1

            for n in range(start, end + 1, step):
                number_as_string = '{0}'.format(n)
                if zfill:
                    number_as_string = number_as_string.zfill(zfill)

                hostname = host.replace(expand_string, number_as_string)
                yield hostname
        else:
            yield host


def make_names_data(inventory_filename=None):
    show_warning()

    config = get_ansible_inventory(inventory_filename)

    host_to_groups = defaultdict(set)
    group_to_hosts = defaultdict(set)
    hosts = []

    # First pass - load hosts/groups of hosts
    for section in config.sections():
        if ':' in section:  # ignore :children and :vars sections this time
            continue

        options = config.options(section)
        for host in _parse_ansible_hosts(options):
            hosts.append(host)
            host_to_groups[host].add(section)
            group_to_hosts[section].add(host)

    # Second pass - load any children groups
    for section in config.sections():
        if not section.endswith(':children'):  # we only support :children for now
            continue

        group_name = section.replace(':children', '')

        options = config.options(section)
        for sub_group_name in options:
            sub_group_hosts = group_to_hosts[sub_group_name]
            for host in sub_group_hosts:
                host_to_groups[host].add(group_name)

    return [
        (host, {}, sorted(list(host_to_groups.get(host))))
        for host in hosts
    ]
