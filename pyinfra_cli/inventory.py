from collections import defaultdict
from os import listdir, path
from types import GeneratorType
from typing import Any, Dict, List, Optional, Tuple, Union

from pyinfra import logger
from pyinfra.api.inventory import Inventory
from pyinfra.context import ctx_inventory
from pyinfra_cli.util import exec_file

# Hosts in an inventory can be just the hostname or a tuple (hostname, data)
ALLOWED_HOST_TYPES = (str, tuple)


def _is_inventory_group(key: str, value: Any):
    """
    Verify that a module-level variable (key = value) is a valid inventory group.
    """

    if key.startswith("_") or not isinstance(value, (list, tuple, GeneratorType)):
        return False

    # If the group is a tuple of (hosts, data), check the hosts
    if isinstance(value, tuple):
        value = value[0]

    # Expand any generators of hosts
    if isinstance(value, GeneratorType):
        value = list(value)

    return all(isinstance(item, ALLOWED_HOST_TYPES) for item in value)


def _get_group_data(dirname: str):
    group_data = {}
    group_data_directory = path.join(dirname, "group_data")

    logger.debug("Checking possible group_data directory: %s", dirname)

    if path.exists(group_data_directory):
        files = listdir(group_data_directory)

        for file in files:
            if not file.endswith(".py"):
                continue

            group_data_file = path.join(group_data_directory, file)
            group_name = path.basename(file)[:-3]

            logger.debug("Looking for group data in: %s", group_data_file)

            # Read the files locals into a dict
            attrs = exec_file(group_data_file, return_locals=True)
            keys = attrs.get("__all__", attrs.keys())

            group_data[group_name] = {
                key: value
                for key, value in attrs.items()
                if key in keys and not key.startswith("_")
            }

    return group_data


def _get_groups_from_filename(inventory_filename: str):
    attrs = exec_file(inventory_filename, return_locals=True)

    return {key: value for key, value in attrs.items() if _is_inventory_group(key, value)}


def make_inventory(
    inventory_filename: str,
    override_data=None,
    cwd: Optional[str] = None,
    group_data_directories=None,
):
    """
    Builds a ``pyinfra.api.Inventory`` from the filesystem. If the file does not exist
    and doesn't contain a / attempts to use that as the only hostname.
    """

    file_groupname = None

    # TODO: this type is complex & convoluted, fix this
    groups: Dict[str, Union[List[str], Tuple[List[str], Dict[str, Any]]]]

    # If we're not a valid file we assume a list of comma separated hostnames
    if not path.exists(inventory_filename):
        groups = {
            "all": inventory_filename.split(","),
        }
    else:
        groups = _get_groups_from_filename(inventory_filename)
        # Used to set all the hosts to an additional group - that of the filename
        # ie inventories/dev.py means all the hosts are in the dev group, if not present
        file_groupname = path.basename(inventory_filename).rsplit(".", 1)[0]

    all_data: Dict[str, Any] = {}

    if "all" in groups:
        all_hosts = groups.pop("all")

        if isinstance(all_hosts, tuple):
            all_hosts, all_data = all_hosts

    # Build all out of the existing hosts if not defined
    else:
        all_hosts = []
        for hosts in groups.values():
            # Groups can be a list of hosts or tuple of (hosts, data)
            hosts = hosts[0] if isinstance(hosts, tuple) else hosts

            for host in hosts:
                # Hosts can be a hostname or tuple of (hostname, data)
                hostname = host[0] if isinstance(host, tuple) else host

                if hostname not in all_hosts:
                    all_hosts.append(hostname)

    groups["all"] = (all_hosts, all_data)

    # Apply the filename group if not already defined
    if file_groupname and file_groupname not in groups:
        groups[file_groupname] = all_hosts

    # In pyinfra an inventory is a combination of (hostnames + data). However, in CLI
    # mode we want to be define this in separate files (inventory / group data). The
    # issue is we want inventory access within the group data files - but at this point
    # we're not ready to make an Inventory. So here we just create a fake one, and
    # attach it to the inventory context while we import the data files.
    logger.debug("Creating fake inventory...")

    fake_groups = {
        # In API mode groups *must* be tuples of (hostnames, data)
        name: group if isinstance(group, tuple) else (group, {})
        for name, group in groups.items()
    }
    fake_inventory = Inventory((all_hosts, all_data), **fake_groups)

    possible_group_data_folders = []
    if cwd:
        possible_group_data_folders.append(cwd)
    inventory_dirname = path.abspath(path.dirname(inventory_filename))
    if inventory_dirname != cwd:
        possible_group_data_folders.append(inventory_dirname)

    if group_data_directories:
        possible_group_data_folders.extend(group_data_directories)

    group_data: Dict[str, Dict[str, Any]] = defaultdict(dict)

    with ctx_inventory.use(fake_inventory):
        for folder in possible_group_data_folders:
            for group_name, data in _get_group_data(folder).items():
                group_data[group_name].update(data)

    # For each group load up any data
    for name, hosts in groups.items():
        data = {}

        if isinstance(hosts, tuple):
            hosts, data = hosts

        if name in group_data:
            data.update(group_data.pop(name))

        # Attach to group object
        groups[name] = (hosts, data)

    # Loop back through any leftover group data and create an empty (for now)
    # group - this is because inventory @connectors can attach arbitrary groups
    # to hosts, so we need to support that.
    for name, data in group_data.items():
        groups[name] = ([], data)

    return (
        Inventory(groups.pop("all"), override_data=override_data, **groups),
        file_groupname and file_groupname.lower(),
    )
