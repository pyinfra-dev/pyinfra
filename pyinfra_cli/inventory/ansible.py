import re

from configparser import ConfigParser

from pyinfra import logger


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
            continue
        yield host


def load_ansible_ini_inventory(inventory_filename):
    logger.info('Trying Ansible inventory format...')

    config = ConfigParser(
        delimiters=(' '),  # we only handle the hostnames for now
        allow_no_value=True,  # we don't by default have = values
        interpolation=None,  # remove any Python interpolation
    )
    config.read(inventory_filename)

    groups = {}

    # First pass - load hosts/groups of hosts
    for section in config.sections():
        if ':' in section:  # ignore :children and :vars sections this time
            continue

        all_hosts = []
        options = config.options(section)
        for option in options:
            all_hosts.extend(_parse_ansible_hosts(options))

        groups[section] = all_hosts

    # Second pass - load any children groups
    for section in config.sections():
        if not section.endswith(':children'):  # we only support :children for now
            continue

        group_name = section.replace(':children', '')

        all_hosts = []
        options = config.options(section)
        for option in options:
            all_hosts.extend(groups[option])

        groups[group_name] = all_hosts

    return groups
