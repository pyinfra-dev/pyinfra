import socket
from collections import defaultdict
from os import listdir, path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

from pyinfra import logger
from pyinfra.api.inventory import Inventory
from pyinfra.connectors.sshuserclient.client import get_ssh_config
from pyinfra.context import ctx_inventory

from .exceptions import CliError
from .util import exec_file, try_import_module_attribute

HostType = Union[str, Tuple[str, Dict]]

# Hosts in an inventory can be just the hostname or a tuple (hostname, data)
ALLOWED_HOST_TYPES = (str, tuple)


def _is_inventory_group(key: str, value: Any):
    """
    Verify that a module-level variable (key = value) is a valid inventory group.
    """

    if key.startswith("__"):
        # Ignore __builtins__/__file__
        return False
    elif key.startswith("_"):
        logger.debug(
            'Ignoring variable "%s" in inventory file since it starts with a leading underscore',
            key,
        )
        return False

    if isinstance(value, list):
        pass
    elif isinstance(value, tuple):
        # If the group is a tuple of (hosts, data), check the hosts
        value = value[0]
    else:
        logger.debug(
            'Ignoring variable "%s" in inventory file since it is not a list or tuple',
            key,
        )
        return False

    if not all(isinstance(item, ALLOWED_HOST_TYPES) for item in value):
        logger.warning(
            'Ignoring host group "%s". '
            "Host groups may only contain strings (host) or tuples (host, data).",
            key,
        )
        return False

    return True


def _get_group_data(dirname_or_filename: str):
    group_data = {}

    logger.debug("Checking possible group_data at: %s", dirname_or_filename)

    if path.exists(dirname_or_filename):
        if path.isfile(dirname_or_filename):
            files = [dirname_or_filename]
        else:
            files = [path.join(dirname_or_filename, file) for file in listdir(dirname_or_filename)]

        for file in files:
            if not file.endswith(".py"):
                continue

            group_name = path.basename(file)[:-3]

            logger.debug("Looking for group data in: %s", file)

            # Read the files locals into a dict
            attrs = exec_file(file, return_locals=True)
            keys = attrs.get("__all__", attrs.keys())

            group_data[group_name] = {
                key: value
                for key, value in attrs.items()
                if key in keys and not key.startswith("__")
            }

    return group_data


def _get_groups_from_filename(inventory_filename: str):
    attrs = exec_file(inventory_filename, return_locals=True)

    return {key: value for key, value in attrs.items() if _is_inventory_group(key, value)}


T = TypeVar("T")


def _get_any_tuple_first(item: Union[T, Tuple[T, Any]]) -> T:
    return item[0] if isinstance(item, tuple) else item


def _resolves_to_host(maybe_host: str) -> bool:
    """Check if a string resolves to a valid IP address."""
    try:
        # Use getaddrinfo to support IPv6 hosts
        socket.getaddrinfo(maybe_host, port=None)
        return True
    except socket.gaierror:
        alias = _get_ssh_alias(maybe_host)
        if not alias:
            return False

        try:
            socket.getaddrinfo(alias, port=None)
            return True
        except socket.gaierror:
            return False


def _get_ssh_alias(maybe_host: str) -> Optional[str]:
    logger.debug('Checking if "%s" is an SSH alias', maybe_host)

    # Note this does not cover the case where `host.data.ssh_config_file` is used
    ssh_config = get_ssh_config()

    if ssh_config is None:
        logger.debug("Could not load SSH config")
        return None

    options = ssh_config.lookup(maybe_host)
    alias = options.get("hostname")

    if alias is None or maybe_host == alias:
        return None

    return alias


def make_inventory(
    inventory: str,
    override_data=None,
    cwd: Optional[str] = None,
    group_data_directories=None,
):
    # (Un)fortunately the CLI is pretty flexible for inventory inputs; we support inventory files, a
    # single hostname, list of hosts, connectors, and python module.function or module:function
    # imports.
    #
    # We check first for an inventory file, a list of hosts or anything with a connector, because
    # (1) an inventory file is a common use case and (2) no other option can have a comma or an @
    # symbol in them.
    is_path_or_host_list_or_connector = (
        path.exists(inventory)
        or "," in inventory
        or "@" in inventory
        # Special case: passing an arbitrary name and specifying --data ssh_hostname=a.b.c
        or (override_data is not None and "ssh_hostname" in override_data)
    )
    if not is_path_or_host_list_or_connector:
        # Next, try loading the inventory from a python function. This happens before checking for a
        # single-host inventory, so that your command does not stop working because somebody
        # registered the domain `my.module.name`.
        inventory_func = try_import_module_attribute(inventory, raise_for_none=False)

        # If the inventory does not refer to a module, we finally check if it refers to a reachable
        # host
        if inventory_func is None and _resolves_to_host(inventory):
            is_path_or_host_list_or_connector = True

    if is_path_or_host_list_or_connector:
        # The inventory is either an inventory file or a (list of) hosts
        return make_inventory_from_files(inventory, override_data, cwd, group_data_directories)
    elif inventory_func is None:
        logger.warning(
            f"{inventory} is neither an inventory file, a (list of) hosts or connectors "
            "nor refers to a python module"
        )
        return Inventory.empty()
    else:
        return make_inventory_from_func(inventory_func, override_data)


def make_inventory_from_func(
    inventory_func: Callable[[], Dict[str, List[HostType]]],
    override_data: Optional[Dict[Any, Any]] = None,
):
    logger.warning("Loading inventory via import function is in alpha!")

    try:
        groups = inventory_func()
    except Exception as e:
        raise CliError(f"Failed to load inventory function: {inventory_func.__name__}: {e}")

    if not isinstance(groups, dict):
        raise TypeError(f"Inventory function {inventory_func.__name__} did not return a dictionary")

    # TODO: this shouldn't be required to make an inventory, groups should suffice
    combined_host_list = set()
    groups_with_data: Dict[str, Tuple[List[HostType], Dict]] = {}

    for key, hosts in groups.items():
        data: Dict = {}

        if isinstance(hosts, tuple):
            hosts, data = hosts

        if not isinstance(data, dict):
            raise TypeError(
                f"Inventory function {inventory_func.__name__} "
                f"group contains non-dictionary data: {key}"
            )

        for host in hosts:
            if not isinstance(host, ALLOWED_HOST_TYPES):
                raise TypeError(
                    f"Inventory function {inventory_func.__name__} invalid host: {host}"
                )

            host = _get_any_tuple_first(host)

            if not isinstance(host, str):
                raise TypeError(
                    f"Inventory function {inventory_func.__name__} invalid host name: {host}"
                )

            combined_host_list.add(host)

        groups_with_data[key] = (hosts, data)

    return Inventory(
        (list(combined_host_list), {}),
        override_data=override_data,
        **groups_with_data,
    )


def make_inventory_from_files(
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
            hosts = _get_any_tuple_first(hosts)
            for host in hosts:
                # Hosts can be a hostname or tuple of (hostname, data)
                hostname = _get_any_tuple_first(host)

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
        possible_group_data_folders.append(path.join(cwd, "group_data"))
    inventory_dirname = path.abspath(path.dirname(inventory_filename))
    if inventory_dirname != cwd:
        possible_group_data_folders.append(path.join(inventory_dirname, "group_data"))

    if group_data_directories:
        possible_group_data_folders.extend(group_data_directories)

    group_data: Dict[str, Dict[str, Any]] = defaultdict(dict)

    with ctx_inventory.use(fake_inventory):
        for folder in possible_group_data_folders:
            for group_name, data in _get_group_data(folder).items():
                group_data[group_name].update(data)
                logger.debug("Adding data to group %s: %r", group_name, data)

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

    return Inventory(groups.pop("all"), override_data=override_data, **groups)
