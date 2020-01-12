from __future__ import division

import re

from pyinfra.api import FactBase, ShortFactBase


class Cpus(FactBase):
    '''
    Returns the number of CPUs on this server.
    '''

    command = 'getconf NPROCESSORS_ONLN 2> /dev/null || getconf _NPROCESSORS_ONLN'

    @staticmethod
    def process(output):
        try:
            return int(output[0])
        except ValueError:
            pass


class Memory(FactBase):
    '''
    Returns the memory installed in this server, in MB.
    '''

    command = 'vmstat -s'

    @staticmethod
    def process(output):
        data = {}

        for line in output:
            value, key = line.split(' ', 1)

            try:
                value = int(value)
            except ValueError:
                continue

            data[key.strip()] = value

        # Easy - Linux just gives us the number
        total_memory = data.get('K total memory', data.get('total memory'))

        # BSD - calculate the total from the # pages and the page size
        if not total_memory:
            bytes_per_page = data.get('bytes per page')
            pages_managed = data.get('pages managed')

            if bytes_per_page and pages_managed:
                total_memory = (pages_managed * bytes_per_page) / 1024

        if total_memory:
            return int(round(total_memory / 1024))


class BlockDevices(FactBase):
    '''
    Returns a dict of (mounted) block devices:

    .. code:: python

        '/dev/sda1': {
            'available': '39489508',
            'used_percent': '3',
            'mount': '/',
            'used': '836392',
            'blocks': '40325900'
        },
        ...
    '''

    command = 'df'
    regex = r'([a-zA-Z0-9\/\-_]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]{1,3})%\s+([a-zA-Z\/0-9\-_]+)'  # noqa: E501
    default = dict

    def process(self, output):
        devices = {}

        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                if matches.group(1) == 'none':
                    continue

                devices[matches.group(1)] = {
                    'blocks': matches.group(2),
                    'used': matches.group(3),
                    'available': matches.group(4),
                    'used_percent': matches.group(5),
                    'mount': matches.group(6),
                }

        return devices


nettools_1_regexes = [
    (
        r'^inet addr:([0-9\.]+).+Bcast:([0-9\.]+).+Mask:([0-9\.]+)$',
        ('ipv4', 'address', 'broadcast', 'netmask'),
    ),
    (
        r'^inet6 addr: ([0-9a-z:]+)\/([0-9]+) Scope:Global',
        ('ipv6', 'address', 'size'),  # COMPAT
        # TODO: rename size -> mask_bits (pre-v0.11 compat)
    ),
]

nettools_2_regexes = [
    (
        r'^inet ([0-9\.]+)\s+netmask ([0-9\.fx]+)(?:\s+broadcast ([0-9\.]+))?$',
        ('ipv4', 'address', 'netmask', 'broadcast'),
    ),
    (
        r'^inet6 ([0-9a-z:]+)\s+prefixlen ([0-9]+)',
        ('ipv6', 'address', 'size'),  # COMPAT
        # TODO: rename size -> mask_bits (pre-v0.11 compat)
    ),
]

iproute2_regexes = [
    (
        r'^inet ([0-9\.]+)\/([0-9]{1,2})(?:\s+brd ([0-9\.]+))?',
        ('ipv4', 'address', 'mask_bits', 'broadcast'),
    ),
    (
        r'^inet6 ([0-9a-z:]+)\/([0-9]{1,3})',
        ('ipv6', 'address', 'mask_bits'),
    ),
]


def _parse_regexes(regexes, lines):
    data = {
        'ipv4': {},
        'ipv6': {},
    }

    for line in lines:
        for regex, groups in regexes:
            matches = re.match(regex, line)
            if matches:
                target_group = data[groups[0]]

                for i, group in enumerate(groups[1:]):
                    target_group[group] = matches.group(i + 1)

                # COMPAT
                # TODO: remove (for forwards compatibility, see above)
                if 'size' in target_group:
                    target_group['mask_bits'] = target_group['size']

                if 'mask_bits' in target_group:
                    target_group['mask_bits'] = int(target_group['mask_bits'])

                break

    return data


class NetworkDevices(FactBase):
    '''
    Gets & returns a dict of network devices. See the ``ipv4_addresses`` and
    ``ipv6_addresses`` facts for easier-to-use shortcuts to get device addresses.

    .. code:: python

        'eth0': {
            'ipv4': {
                'address': '127.0.0.1',
                'broadcast': '127.0.0.13',
                # Only one of these will exist:
                'netmask': '255.255.255.255',
                'mask_bits': '32'
            },
            'ipv6': {
                'address': 'fe80::a00:27ff:fec3:36f0',
                'mask_bits': '64'
            }
        },
        ...
    '''

    command = 'ip addr show 2> /dev/null || ifconfig'
    default = dict

    # Definition of valid interface names for Linux:
    # https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/net/core/dev.c?h=v5.1.3#n1020
    _start_regexes = [
        (
            r'^([^/: \s]+)\s+Link encap:',
            lambda lines: _parse_regexes(nettools_1_regexes, lines),
        ),
        (
            r'^([^/: \s]+): flags=',
            lambda lines: _parse_regexes(nettools_2_regexes, lines),
        ),
        (
            r'^[0-9]+: ([^/: \s]+): ',
            lambda lines: _parse_regexes(iproute2_regexes, lines),
        ),
    ]

    def process(self, output):
        devices = {}

        # Store current matches (start lines), the handler and any lines
        matches = None
        handler = None
        line_buffer = []

        for line in output:
            matched = False

            # Look for start lines
            for regex, new_handler in self._start_regexes:
                new_matches = re.match(regex, line)

                # If we find a start line
                if new_matches:
                    matched = True

                    # Assign any current matches with current handler, reset buffer
                    if matches:
                        devices[matches.group(1)] = handler(line_buffer)
                        line_buffer = []

                    # Set new matches/handler
                    matches = new_matches
                    handler = new_handler
                    break

            if not matched:
                line_buffer.append(line)

        # Handle any left over matches
        if matches:
            devices[matches.group(1)] = handler(line_buffer)

        return devices


class Ipv4Addresses(ShortFactBase):
    '''
    Gets & returns a dictionary of network interface -> IPv4 address.

    .. code:: python

        'eth0': '127.0.0.1',
        ...
    '''

    fact = NetworkDevices
    ip_type = 'ipv4'

    def process_data(self, data):
        addresses = {}

        for interface, details in data.items():
            ip_details = details.get(self.ip_type)
            if not ip_details:
                continue  # pramga: no cover

            addresses[interface] = ip_details['address']

        return addresses


class Ipv6Addresses(Ipv4Addresses):
    '''
    Gets & returns a dictionary of network interface -> IPv6 address.

    .. code:: python

        'eth0': 'fe80::a00:27ff::2',
        ...
    '''

    ip_type = 'ipv6'
