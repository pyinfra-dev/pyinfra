import json
import re

from collections import defaultdict
from configparser import ConfigParser
from os import path

try:
    import yaml
except ImportError:
    yaml = None

from pyinfra import logger
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import memoize


@memoize
def show_warning():
    logger.warning('The @ansible connector is in alpha!')


def make_names_data(inventory_filename=None):
    show_warning()

    if not inventory_filename:
        raise InventoryError('No Ansible inventory filename provided!')

    if not path.exists(inventory_filename):
        raise InventoryError((
            'Could not find Ansible inventory file: {0}'
        ).format(inventory_filename))

    return parse_inventory(inventory_filename)


def parse_inventory(inventory_filename):
    # fallback to INI if no extension
    extension = inventory_filename.split('.')[-1] if '.' in inventory_filename else 'ini'

    # host:set(groups) mapping
    host_to_groups = {}

    if extension in ['ini']:
        host_to_groups = parse_inventory_ini(inventory_filename)
    elif extension in ['json']:
        with open(inventory_filename) as inventory_file:
            inventory_tree = json.load(inventory_file)
            # close file early
        host_to_groups = parse_inventory_tree(inventory_tree)
    elif extension in ['yaml', 'yml']:
        if yaml is None:
            raise Exception((
                'To parse YAML Ansible inventories requires `pyyaml`. '
                'Install it with `pip install pyyaml`.'
            ))
        with open(inventory_filename) as inventory_file:
            inventory_tree = yaml.safe_load(inventory_file)
            # close file early
        host_to_groups = parse_inventory_tree(inventory_tree)
    else:
        raise InventoryError((
            'Ansible inventory file format not supported: {0}'
        ).format(extension))

    return [
        (host, {}, sorted(list(host_to_groups.get(host))))
        for host in host_to_groups
    ]


def parse_inventory_ini(inventory_filename):
    config = ConfigParser(
        delimiters=(' '),  # we only handle the hostnames for now
        allow_no_value=True,  # we don't by default have = values
        interpolation=None,  # remove any Python interpolation
    )
    config.read(inventory_filename)

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

    return host_to_groups


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


def parse_inventory_tree(inventory_tree, host_to_groups=dict(), group_stack=set()):
    for group in inventory_tree:
        # set logic adds tolerance for duplicate group names
        groups = group_stack.union({group})

        if 'hosts' in inventory_tree[group]:
            for host in inventory_tree[group]['hosts']:
                append_groups_to_host(host, groups, host_to_groups)

        if 'children' in inventory_tree[group]:
            # recursively parse inventory tree
            parse_inventory_tree(inventory_tree[group]['children'], host_to_groups, groups)

    return host_to_groups


def append_groups_to_host(host, groups, host_to_groups):
    if host in host_to_groups:
        # set logic handles de-duplication
        host_to_groups[host] = host_to_groups[host].union(groups)
    else:
        host_to_groups[host] = groups
