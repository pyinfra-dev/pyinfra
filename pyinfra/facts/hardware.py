from __future__ import annotations

import re

from pyinfra.api import FactBase, ShortFactBase


class Cpus(FactBase):
    """
    Returns the number of CPUs on this server.
    """

    command = "getconf NPROCESSORS_ONLN 2> /dev/null || getconf _NPROCESSORS_ONLN"

    @staticmethod
    def process(output):
        try:
            return int(output[0])
        except ValueError:
            pass


class Memory(FactBase):
    """
    Returns the memory installed in this server, in MB.
    """

    command = "vmstat -s"
    requires_command = "vmstat"

    @staticmethod
    def process(output):
        data = {}

        for line in output:
            line = line.strip()
            value, key = line.split(" ", 1)

            try:
                value = int(value)
            except ValueError:
                continue

            data[key.strip()] = value

        # Easy - Linux just gives us the number
        total_memory = data.get("K total memory", data.get("total memory"))

        # BSD - calculate the total from the # pages and the page size
        if not total_memory:
            bytes_per_page = data.get("bytes per page")
            pages_managed = data.get("pages managed")

            if bytes_per_page and pages_managed:
                total_memory = (pages_managed * bytes_per_page) / 1024

        if total_memory:
            return int(round(total_memory / 1024))


class BlockDevices(FactBase):
    """
    Returns a dict of (mounted) block devices:

    .. code:: python

        {
            "/dev/sda1": {
                "available": "39489508",
                "used_percent": "3",
                "mount": "/",
                "used": "836392",
                "blocks": "40325900"
            },
        }
    """

    command = "df"
    regex = r"([a-zA-Z0-9\/\-_]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]{1,3})%\s+([a-zA-Z\/0-9\-_]+)"  # noqa: E501
    default = dict

    def process(self, output):
        devices = {}

        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                if matches.group(1) == "none":
                    continue

                devices[matches.group(1)] = {
                    "blocks": matches.group(2),
                    "used": matches.group(3),
                    "available": matches.group(4),
                    "used_percent": matches.group(5),
                    "mount": matches.group(6),
                }

        return devices


class NetworkDevices(FactBase):
    """
    Gets & returns a dict of network devices. See the ``ipv4_addresses`` and
    ``ipv6_addresses`` facts for easier-to-use shortcuts to get device addresses.

    .. code:: python
        "enp1s0": {
            "ether": "12:34:56:78:9A:BC",
            "mtu": 1500,
            "state": "UP",
            "ipv4": {
                "address": "192.168.1.100",
                "mask_bits": 24,
                "netmask": "255.255.255.0"
            },
            "ipv6": {
                "address": "2001:db8:85a3::8a2e:370:7334",
                "mask_bits": 64,
                "additional_ips": [
                    {
                        "address": "fe80::1234:5678:9abc:def0",
                        "mask_bits": 64
                    }
                ]
            }
        },
        "incusbr0": {
            "ether": "DE:AD:BE:EF:CA:FE",
            "mtu": 1500,
            "state": "UP",
            "ipv4": {
                "address": "10.0.0.1",
                "mask_bits": 24,
                "netmask": "255.255.255.0"
            },
            "ipv6": {
                "address": "fe80::dead:beef:cafe:babe",
                "mask_bits": 64,
                "additional_ips": [
                    {
                        "address": "2001:db8:1234:5678::1",
                        "mask_bits": 64
                    }
                ]
            }
        },
        "lo": {
            "mtu": 65536,
            "state": "UP",
            "ipv6": {
                "address": "::1",
                "mask_bits": 128
            }
        },
        "veth98806fd6": {
            "ether": "AA:BB:CC:DD:EE:FF",
            "mtu": 1500,
            "state": "UP"
        },
        "vethda29df81": {
            "ether": "11:22:33:44:55:66",
            "mtu": 1500,
            "state": "UP"
        },
        "wlo1": {
            "ether": "77:88:99:AA:BB:CC",
            "mtu": 1500,
            "state": "UNKNOWN"
        }
    """

    command = "ip addr show 2> /dev/null || ifconfig -a"
    default = dict

    # Definition of valid interface names for Linux:
    # https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/net/core/dev.c?h=v5.1.3#n1020
    def process(self, output):
        def mask(value):
            try:
                if value.startswith("0x"):
                    mask_bits = bin(int(value, 16)).count("1")
                else:
                    mask_bits = int(value)
                netmask = ".".join(
                    str((0xFFFFFFFF << (32 - b) >> mask_bits) & 0xFF) for b in (24, 16, 8, 0)
                )
            except ValueError:
                mask_bits = sum(bin(int(x)).count("1") for x in value.split("."))
                netmask = value

            return mask_bits, netmask

        # Strip lines and merge them as a block of text
        output = "\n".join(map(str.strip, output))

        # Splitting the output into sections per network device
        device_sections = re.split(r"\n(?=\d+: \w|\w+:.*mtu.*)", output)

        # Dictionary to hold all device information
        all_devices = {}

        for section in device_sections:
            # Extracting the device name
            device_name_match = re.match(r"^(?:\d+: )?([\w@]+):", section)
            if not device_name_match:
                continue
            device_name = device_name_match.group(1)

            # Regular expressions to match different parts of the output
            ether_re = re.compile(r"([0-9A-Fa-f:]{17})")
            mtu_re = re.compile(r"mtu (\d+)")
            ipv4_re = (
                re.compile(
                    r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)(?: brd (\d+\.\d+\.\d+\.\d+))"
                ),  # ip a output,
                re.compile(
                    r"inet (\d+\.\d+\.\d+\.\d+)\s+netmask\s+((?:\d+\.\d+\.\d+\.\d+)|(?:[0-9a-fA-FxX]+))(?:\s+broadcast\s+(\d+\.\d+\.\d+\.\d+))"  # noqa: E501
                ),  # ifconfig -a output
            )

            # Parsing the output
            ether = ether_re.search(section)
            mtu = mtu_re.search(section)

            # Building the result dictionary for the device
            device_info = {}
            if ether:
                device_info["ether"] = ether.group(1)
            if mtu:
                device_info["mtu"] = int(mtu.group(1))

            device_info["state"] = (
                "UP" if "UP" in section else "DOWN" if "DOWN" in section else "UNKNOWN"
            )

            # IPv4 Addresses
            for ipv4_re_ in ipv4_re:
                ipv4_matches = ipv4_re_.findall(section)
                if ipv4_matches:
                    break

            if ipv4_matches:
                ipv4_info = []
                for ipv4 in ipv4_matches:
                    address = ipv4[0]
                    mask_value = ipv4[1]
                    mask_bits, netmask = mask(mask_value)
                    broadcast = ipv4[2] if len(ipv4) == 3 else None

                    ipv4_info.append(
                        {
                            "address": address,
                            "mask_bits": mask_bits,
                            "netmask": netmask,
                            "broadcast": broadcast,
                        },
                    )
                device_info["ipv4"] = ipv4_info[0]
                if len(ipv4_matches) > 1:
                    device_info["ipv4"]["additional_ips"] = ipv4_info[1:]  # type: ignore[index]

            # IPv6 Addresses
            ipv6_re = (
                re.compile(r"inet6\s+([0-9a-fA-F:]+)/(\d+)"),
                re.compile(r"inet6\s+([0-9a-fA-F:]+)\s+prefixlen\s+(\d+)"),
            )

            for ipv6_re_ in ipv6_re:
                ipv6_matches = ipv6_re_.findall(section)
                if ipv6_matches:
                    break

            if ipv6_matches:
                ipv6_info = []
                for ipv6 in ipv6_matches:
                    address = ipv6[0]
                    mask_bits = ipv6[1] or ipv6[2]
                    ipv6_info.append({"address": address, "mask_bits": int(mask_bits)})
                device_info["ipv6"] = ipv6_info[0]
                if len(ipv6_matches) > 1:
                    device_info["ipv6"]["additional_ips"] = ipv6_info[1:]  # type: ignore[index]

            all_devices[device_name] = device_info

        return all_devices


class Ipv4Addrs(ShortFactBase):
    """
    Gets & returns a dictionary of network interface -> list of IPv4 addresses.

    .. code:: python

        {
            "eth0": ["127.0.0.1"],
        }

    .. note::
        Network interfaces with no IPv4 will not be part of the dictionary.
    """

    fact = NetworkDevices
    ip_type = "ipv4"

    def process_data(self, data):
        host_to_ips = {}

        for interface, details in data.items():
            ips = []

            ip_details = details.get(self.ip_type)
            if not ip_details or not ip_details.get("address"):
                continue

            ips.append(ip_details["address"])
            if "additional_ips" in ip_details:
                ips.extend([ip["address"] for ip in ip_details["additional_ips"]])

            host_to_ips[interface] = ips

        return host_to_ips


class Ipv6Addrs(Ipv4Addrs):
    """
    Gets & returns a dictionary of network interface -> list of IPv6 addresses.

    .. code:: python

        {
            "eth0": ["fe80::a00:27ff::2"],
        }

    .. note::
        Network interfaces with no IPv6 will not be part of the dictionary.
    """

    ip_type = "ipv6"


# TODO: remove these in v3
# Legacy versions of the above that only support one IP per interface
#


class Ipv4Addresses(ShortFactBase):
    """
    Gets & returns a dictionary of network interface -> IPv4 address.

    .. code:: python

        {
            "eth0": "127.0.0.1",
        }

    .. warning::
        This fact is deprecated, please use the ``hardware.Ipv4Addrs`` fact.

    .. note::
        Network interfaces with no IPv4 will not be part of the dictionary.
    """

    fact = NetworkDevices
    ip_type = "ipv4"

    def process_data(self, data):
        addresses = {}

        for interface, details in data.items():
            ip_details = details.get(self.ip_type)
            if not ip_details or not ip_details.get("address"):
                continue  # pragma: no cover

            addresses[interface] = ip_details["address"]

        return addresses


class Ipv6Addresses(Ipv4Addresses):
    """
    Gets & returns a dictionary of network interface -> IPv6 address.

    .. code:: python

        {
            "eth0": "fe80::a00:27ff::2",
        }

    .. warning::
        This fact is deprecated, please use the ``hardware.Ipv6Addrs`` fact.

    .. note::
        Network interfaces with no IPv6 will not be part of the dictionary.
    """

    ip_type = "ipv6"
