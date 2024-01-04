"""
Gather the information provided by ``opkg`` on OpenWrt systems:
    + ``opkg`` configuration
    + feeds configuration
    + list of installed packages
    + list of packages with available upgrades


    see https://openwrt.org/docs/guide-user/additional-software/opkg
"""
import re
from typing import Dict, NamedTuple, Union

from pyinfra import logger
from pyinfra.api import FactBase
from pyinfra.facts.util.packaging import parse_packages

# TODO - change NamedTuple to dataclass but need to figure out how to get json serialization
#        to work without changing core code


class PkgUpgradeInfo(NamedTuple):
    installed: str
    available: str


class ConfInfo(NamedTuple):
    paths: Dict[str, str]  # list of paths, e.g. {'root':'/', 'ram':'/tmp}
    list_dir: str  # where package lists are stored, e.g. /var/opkg-lists
    options: Dict[
        str, Union[str, bool]
    ]  # mapping from option to value, e.g. {'check_signature': True}
    arch_cfg: Dict[str, int]  # priorities for architectures


class FeedInfo(NamedTuple):
    url: str  # url for the feed
    fmt: str  # format of the feed, e.g. "src/gz"
    kind: str  # whether it comes from the 'distribution' or is 'custom'


class Conf(FactBase):
    """
    Returns a NamedTuple with the current configuration:

    .. code:: python

        ConfInfo(
            paths = {
                "root": "/",
                "ram": "/tmp",
            },
            list_dir = "/opt/opkg-lists",
            options = {
                "overlay_root": "/overlay"
            },
            arch_cfg = {
                "all": 1,
                "noarch": 1,
                "i386_pentium": 10
            }
        )

    """

    regex = re.compile(
        r"""
                       ^(?:\s*)
                       (?:
                       (?:arch\s+(?P<arch>\w+)\s+(?P<priority>\d+))|
                       (?:dest\s+(?P<dest>\w+)\s+(?P<dest_path>[\w/\-]+))|
                       (?:lists_dir\s+(?P<lists_dir>ext)\s+(?P<list_path>[\w/\-]+))|
                       (?:option\s+(?P<option>\w+)(?:\s+(?P<value>[^#]+))?)
                       )?
                       (?:\s*\#.*)?
                       $
                       """,
        re.X,
    )
    conf_file = "/etc/opkg.conf"
    command = f"cat {conf_file}"
    default = lambda x: ConfInfo({}, "", {}, {})  # noqa:

    def process(self, output):
        dest, lists_dir, options, arch_cfg = {}, "", {}, {}
        for line in output:
            match = self.regex.match(line)

            if match is None:
                logger.warning(f"Opkg: could not parse opkg.conf line '{line}'")
            elif match.group("arch") is not None:
                arch_cfg[match.group("arch")] = int(match.group("priority"))
            elif match.group("dest") is not None:
                dest[match.group("dest")] = match.group("dest_path")
            elif match.group("lists_dir") is not None:
                lists_dir = match.group("list_path")
            elif match.group("option") is not None:
                options[match.group("option")] = match.group("value") or True

        return ConfInfo(dest, lists_dir, options, arch_cfg)


class Feeds(FactBase):
    """
    Returns a dictionary containing the information for the distribution-provided and
    custom opkg feeds:

    .. code:: python

        {
         'openwrt_base': FeedInfo(url='http://downloads ... /i386_pentium/base', fmt='src/gz', kind='distribution'), # noqa: E501
         'openwrt_core': FeedInfo(url='http://downloads ... /x86/geode/packages', fmt='src/gz', kind='distribution'), # noqa: E501
         'openwrt_luci': FeedInfo(url='http://downloads ... /i386_pentium/luci', fmt='src/gz', kind='distribution'),# noqa: E501
         'openwrt_packages': FeedInfo(url='http://downloads ... /i386_pentium/packages', fmt='src/gz', kind='distribution'),# noqa: E501
         'openwrt_routing': FeedInfo(url='http://downloads ... /i386_pentium/routing', fmt='src/gz', kind='distribution'),# noqa: E501
         'openwrt_telephony': FeedInfo(url='http://downloads ... /i386_pentium/telephony', fmt='src/gz', kind='distribution') # noqa: E501
        }
    """

    regex = re.compile(
        r"^(CUSTOM)|(?:\s*(?P<fmt>[\w/]+)\s+(?P<name>[\w]+)\s+(?P<url>[\w./:]+))?(?:\s*#.*)?$"
    )
    command = "cat /etc/opkg/distfeeds.conf; echo CUSTOM; cat /etc/opkg/customfeeds.conf"
    default = dict

    def process(self, output):
        feeds, kind = {}, "distribution"
        for line in output:
            match = self.regex.match(line)

            if match is None:
                logger.warning(f"Opkg: could not parse /etc/opkg/*feeds.conf line '{line}'")
            elif match.group(0) == "CUSTOM":
                kind = "custom"
            elif match.group("name") is not None:
                feeds[match.group("name")] = FeedInfo(match.group("url"), match.group("fmt"), kind)

        return feeds


class InstallableArchitectures(FactBase):
    """
    Returns a dictionary containing the currently installable architectures for this system along
    with their priority:

    .. code:: python

       {
         'all': 1,
         'i386_pentium': 10,
         'noarch': 1
        }
    """

    regex = re.compile(r"^(?:\s*arch\s+(?P<arch>[\w]+)\s+(?P<prio>\d+))?(\s*#.*)?$")
    command = "/bin/opkg print-architecture"
    default = dict

    def process(self, output):
        arch_list = {}
        for line in output:
            match = self.regex.match(line)

            if match is None:
                logger.warning(f"could not parse arch line '{line}'")
            elif match.group("arch") is not None:
                arch_list[match.group("arch")] = int(match.group("prio"))

        return arch_list


class Packages(FactBase):
    """
    Returns a dict of installed opkg packages:

    .. code:: python

       {
         'package_name': ['version'],
         ...
       }
    """

    command = "/bin/opkg list-installed"
    regex = r"^([a-zA-Z0-9][\w\-\.]*)\s-\s([\w\-\.]+)"
    default = dict

    def process(self, output):
        return parse_packages(self.regex, sorted(output))


class UpgradeablePackages(FactBase):
    """
    Returns a dict of installed and upgradable opkg packages:

    .. code:: python

        {
          'package_name': (installed='1.2.3', available='1.2.8')
          ...
        }
    """

    command = "/bin/opkg list-upgradable"  # yes, really spelled that way
    regex = re.compile(r"^([a-zA-Z0-9][\w\-.]*)\s-\s([\w\-.]+)\s-\s([\w\-.]+)")
    default = dict
    use_default_on_error = True

    def process(self, output):
        result = {}
        for line in output:
            match = self.regex.match(line)
            if match and len(match.groups()) == 3:
                result[match.group(1)] = PkgUpgradeInfo(match.group(2), match.group(3))
            else:
                logger.warning(f"Opkg: could not list-upgradable line '{line}'")

        return result
