from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Literal, cast

from typing_extensions import NotRequired, TypedDict, override

from pyinfra import logger
from pyinfra.api import FactBase, ShortFactBase


class CpuInfo(FactBase):
    """
    Returns dict of information returned by lscpu command.

    .. code:: python

        {
            "Architecture": "x86_64",
            "CPU op-mode(s)": "32-bit, 64-bit",
            "Address sizes": "36 bits physical, 48 bits virtual",
            "Byte Order": "Little Endian",
            "CPU(s)": "4",
            "On-line CPU(s) list": "0-3",
            "Vendor ID": "GenuineIntel",
            "Model name": "Intel(R) Atom(TM) CPU N2800   @ 1.86GHz",
            "CPU family": "6",
            "Model": "54",
            "Thread(s) per core": "2",
            "Core(s) per socket": "2",
            "Socket(s)": "1",
            "Stepping": "1",
            "CPU(s) scaling MHz": "48%",
            "CPU max MHz": "1862,0000",
            "CPU min MHz": "798,0000",
            "BogoMIPS": "3735,20",
            "Flags": [
                "fpu",
                "vme",
                "de",
                "pse",
                "tsc",
                "msr",
                "pae",
                "mce",
                "cx8",
                "apic",
                "sep",
                "mtrr",
                "pge",
                "mca",
                "cmov",
                "pat",
                "pse36",
                "clflush",
                "dts",
                "acpi",
                "mmx",
                "fxsr",
                "sse",
                "sse2",
                "ss",
                "ht",
                "tm",
                "pbe",
                "syscall",
                "nx",
                "lm",
                "constant_tsc",
                "arch_perfmon",
                "pebs",
                "bts",
                "nopl",
                "nonstop_tsc",
                "cpuid",
                "aperfmperf",
                "pni",
                "dtes64",
                "monitor",
                "ds_cpl",
                "est",
                "tm2",
                "ssse3",
                "cx16",
                "xt",
                "pr",
                "pdcm",
                "movbe",
                "lahf_lm",
                "dtherm",
                "arat"
            ],
            "L1d cache": "48 KiB (2 instances)",
            "L1i cache": "64 KiB (2 instances)",
            "L2 cache": "1 MiB (2 instances)",
            "NUMA node(s)": "1",
            "NUMA node0 CPU(s)": "0-3",
            "Vulnerability Itlb multihit": "Not affected",
            "Vulnerability L1tf": "Not affected",
            "Vulnerability Mds": "Not affected",
            "Vulnerability Meltdown": "Not affected",
            "Vulnerability Spec store bypass": "Not affected",
            "Vulnerability Spectre v1": "Not affected",
            "Vulnerability Spectre v2": "Not affected",
            "Vulnerability Srbds": "Not affected",
            "Vulnerability Tsx async abort": "Not affected"
        }
    """

    @override
    def command(self) -> str:
        return "LANG=C lscpu"

    @override
    def requires_command(self) -> str:
        return "lscpu"

    @override
    def process(self, output):
        if output:
            cpu_info = {}
            for info in output:
                info_data = info.split(":")
                if "flag" in info_data[0].strip().lower():
                    data = info_data[1].strip().split()
                else:
                    data = info_data[1].strip()
                cpu_info[info_data[0].strip()] = data
            return cpu_info
        return None


class Cpus(FactBase[int]):
    """
    Returns the number of CPUs on this server.
    """

    @override
    def command(self) -> str:
        return "getconf NPROCESSORS_ONLN 2> /dev/null || getconf _NPROCESSORS_ONLN"

    @override
    def process(self, output):
        try:
            return int(list(output)[0])
        except ValueError:
            pass


class Memory(FactBase):
    """
    Returns the memory installed in this server, in MB.
    """

    @override
    def requires_command(self) -> str:
        return "vmstat"

    @override
    def command(self) -> str:
        return "LANG=C vmstat -s"

    @override
    def process(self, output):
        data = {}

        for line in output:
            line = line.strip()
            value, key = line.split(" ", 1)

            try:
                value = float(value)
            except ValueError:
                continue

            data[key.strip()] = value

        # Easy - Linux just gives us the number
        total_memory = data.get("K total memory", data.get("total memory"))

        # BSD - calculate the total from the # pages and the page size
        if not total_memory:
            bytes_per_page = data.get("bytes per page")
            pages_managed = data.get("pages managed")

            # FreeBSD doesn't report "pages managed", sum page categories instead
            if not pages_managed:
                page_keys = (
                    "pages active",
                    "pages inactive",
                    "pages wired down",
                    "pages free",
                    "pages in the laundry queue",
                )
                page_counts = [data.get(k, 0) for k in page_keys]
                if any(page_counts):
                    pages_managed = sum(page_counts)

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

    regex = r"([a-zA-Z0-9\/\-_]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]{1,3})%\s+([a-zA-Z\/0-9\-_]+)"  # noqa: E501
    default = dict

    @override
    def command(self) -> str:
        return "df"

    @override
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


AddressFamilyType = Literal["ipv4", "ipv6"]


class AddrInfoType(TypedDict):
    address: str
    broadcast: NotRequired[str | None]
    mask_bits: NotRequired[int]
    netmask: NotRequired[str]
    additional_ips: NotRequired[list[AddrInfoType]]


class DevInfoType(TypedDict):
    ether: NotRequired[str]
    mtu: NotRequired[int]
    state: str
    ipv4: NotRequired[AddrInfoType]
    ipv6: NotRequired[AddrInfoType]


NtwkDevMapType = dict[str, DevInfoType]


class NetworkDevices(FactBase[NtwkDevMapType]):
    """
    Gets & returns a dict of network devices. See the ``ipv4_addresses`` and
    ``ipv6_addresses`` facts for easier-to-use shortcuts to get device addresses.

    .. code:: python
        {
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
        }
    """

    default = dict

    @override
    def command(self) -> str:
        return "ip -j addr show 2> /dev/null || ip addr show 2> /dev/null || ifconfig -a"

    @staticmethod
    def mask(value: str) -> tuple[int, str]:
        try:
            mask_bits = int(value, 16).bit_count() if value.startswith("0x") else int(value)
            netmask = ".".join(
                str((0xFFFFFFFF << (32 - b) >> mask_bits) & 0xFF) for b in (24, 16, 8, 0)
            )
        except ValueError:
            mask_bits = sum(int(x).bit_count() for x in value.split("."))
            netmask = value

        return mask_bits, netmask

    def ntwk_info_from_json(self, json_data: Sequence[str]) -> NtwkDevMapType:
        """
        Example JSON output from ip -j addr show:
        {
            "ifindex": 2,
            "ifname": "enp3s0",
            "flags": [
              "BROADCAST",
              "MULTICAST",
              "UP",
              "LOWER_UP"
            ],
            "mtu": 1500,
            "qdisc": "fq_codel",
            "operstate": "UP",
            "group": "default",
            "txqlen": 1000,
            "link_type": "ether",
            "address": "58:11:22:af:50:41",
            "broadcast": "ff:ff:ff:ff:ff:ff",
            "altnames": [
              "enx581122af5041"
            ],
            "addr_info": [
              {
                "family": "inet",
                "local": "192.168.21.73",
                "prefixlen": 24,
                "broadcast": "192.168.21.255",
                "scope": "global",
                "dynamic": true,
                "noprefixroute": true,
                "label": "enp3s0",
                "valid_life_time": 34647,
                "preferred_life_time": 34647
              },
              {
                "family": "inet6",
                "local": "2607:4357:bd44:7901::18d2",
                "prefixlen": 128,
                "scope": "global",
                "dynamic": true,
                "noprefixroute": true,
                "valid_life_time": 31669,
                "preferred_life_time": 31669
              },
            ]
          },
        """

        result, error = {}, False
        try:
            decoded = json.loads("\n".join(json_data))
        except (json.JSONDecodeError, TypeError, UnicodeDecodeError, RecursionError):
            decoded, error = {}, True

        for info in decoded:
            device: DevInfoType = {"state": info.get("operstate") or "UNKNOWN"}
            if "address" in info:
                device["ether"] = info["address"]
            if "mtu" in info:
                device["mtu"] = info["mtu"]

            for addr_info in info.get("addr_info", []):
                # if there isn't a local address or the address family is missing, give up
                if ("local" not in addr_info) or (
                    family := {"inet": "ipv4", "inet6": "ipv6"}.get(addr_info.get("family"))
                ) is None:
                    error = True  # keep going but log error in parsing
                    continue

                addr_blk: AddrInfoType
                if family == "ipv4":
                    addr_blk = {
                        "address": addr_info["local"],
                        "broadcast": addr_info.get("broadcast"),
                    }
                    if "prefixlen" in addr_info:
                        addr_blk["mask_bits"] = addr_info["prefixlen"]
                        addr_blk["netmask"] = self.mask(str(addr_info["prefixlen"]))[1]
                elif family == "ipv6":
                    addr_blk = {"address": addr_info["local"]}
                    if "prefixlen" in addr_info:
                        addr_blk["mask_bits"] = addr_info["prefixlen"]
                family = cast("AddressFamilyType", family)  # if we're here it isn't None
                if family not in device:
                    device[family] = addr_blk
                else:
                    if "additional_ips" not in device[family]:
                        device[family]["additional_ips"] = []
                    device[family]["additional_ips"].append(addr_blk)

            if "ifname" in info:
                result[info["ifname"]] = device
            else:
                error = True

        if error:
            logger.error(f"Error decoding ip address output: '{json_data}'")

        return result

    # Definition of valid interface names for Linux:
    # https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/net/core/dev.c?h=v5.1.3#n1020
    @override
    def process(self, output: Sequence[str]) -> NtwkDevMapType:
        if "".join(map(str.strip, output[:2])).startswith("[{"):
            return self.ntwk_info_from_json(output)

        # Strip lines and merge them as a block of text
        output = "\n".join(map(str.strip, output))

        # Splitting the output into sections per network device
        device_sections = re.split(r"\n(?=\d+: [^\s/:]|[^\s/:]+:.*mtu )", output)

        # Dictionary to hold all device information
        all_devices: NtwkDevMapType = {}

        for section in device_sections:
            # Extracting the device name
            device_name_match = re.match(r"^(?:\d+: )?([^\s/:]+):", section)
            if not device_name_match:
                continue
            device_name = device_name_match.group(1)

            # Regular expressions to match different parts of the output
            ether_re = re.compile(r"ether ([0-9A-Fa-f:]{17})")
            mtu_re = re.compile(r"mtu (\d+)")
            ipv4_re = (
                # ip a
                re.compile(
                    r"inet (?P<address>\d+\.\d+\.\d+\.\d+)/(?P<mask>\d+)(?: metric \d+)?(?: brd (?P<broadcast>\d+\.\d+\.\d+\.\d+))?"  # noqa: E501
                ),
                # ifconfig -a
                re.compile(
                    r"inet (?P<address>\d+\.\d+\.\d+\.\d+)\s+netmask\s+(?P<mask>(?:\d+\.\d+\.\d+\.\d+)|(?:[0-9a-fA-FxX]+))(?:\s+broadcast\s+(?P<broadcast>\d+\.\d+\.\d+\.\d+))?"  # noqa: E501
                ),
            )
            ipv6_re = (
                # ip a
                re.compile(r"inet6\s+(?P<address>[0-9a-fA-F:]+)/(?P<mask>\d+)"),
                # ifconfig -a
                re.compile(r"inet6\s+(?P<address>[0-9a-fA-F:]+)\s+prefixlen\s+(?P<mask>\d+)"),
            )

            # Parsing the output
            ether = ether_re.search(section)
            mtu = mtu_re.search(section)

            # Building the result dictionary for the device
            device_info: DevInfoType = {
                "state": "UP" if "UP" in section else "DOWN" if "DOWN" in section else "UNKNOWN"
            }
            if ether:
                device_info["ether"] = ether.group(1)
            if mtu:
                device_info["mtu"] = int(mtu.group(1))

            # IPv4 Addresses
            ipv4_matches: list[re.Match[str]] = []
            for ipv4_re_ in ipv4_re:
                ipv4_matches = list(ipv4_re_.finditer(section))
                if len(ipv4_matches) > 0:
                    break

            if len(ipv4_matches) > 0:
                ipv4_info: list[AddrInfoType] = []
                for ipv4 in ipv4_matches:
                    address = ipv4.group("address")
                    mask_value = ipv4.group("mask")
                    mask_bits, netmask = self.mask(mask_value)
                    try:
                        broadcast = ipv4.group("broadcast")
                    except IndexError:
                        broadcast = None

                    addr_info: AddrInfoType = {
                        "address": address,
                        "mask_bits": mask_bits,
                        "netmask": netmask,
                        "broadcast": broadcast,
                    }
                    ipv4_info.append(addr_info)
                device_info["ipv4"] = ipv4_info[0]
                if len(ipv4_matches) > 1:
                    device_info["ipv4"]["additional_ips"] = ipv4_info[1:]

            # IPv6 Addresses
            ipv6_matches: list[re.Match[str]] = []
            for ipv6_re_ in ipv6_re:
                ipv6_matches = list(ipv6_re_.finditer(section))
                if ipv6_matches:
                    break

            if len(ipv6_matches) > 0:
                ipv6_info: list[AddrInfoType] = []
                for ipv6 in ipv6_matches:
                    address = ipv6.group("address")
                    mask_bits_str = ipv6.group("mask")
                    ipv6_info.append({"address": address, "mask_bits": int(mask_bits_str)})
                device_info["ipv6"] = ipv6_info[0]
                if len(ipv6_matches) > 1:
                    device_info["ipv6"]["additional_ips"] = ipv6_info[1:]

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

    @override
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

    @override
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
