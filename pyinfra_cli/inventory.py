# pyinfra
# File: pyinfra_cli/inventory.py
# Desc: inventory creation for the CLI

from fnmatch import fnmatch
from os import listdir, path
from types import GeneratorType

import six

from pyinfra import logger, pseudo_inventory
from pyinfra.api.inventory import Inventory
from pyinfra.api.util import exec_file

# Hosts in an inventory can be just the hostname or a tuple (hostname, data)
ALLOWED_HOST_TYPES = tuple(
    six.string_types + (tuple,),
)

# Group data can be any "core" Python type
ALLOWED_DATA_TYPES = tuple(
    six.string_types + six.integer_types
    + (bool, dict, list, set, tuple, float, complex),
)


def is_inventory_group(key, value):
    '''
    Verify that a module-level variable (key = value) is a valid inventory group.
    '''

    if (
        key.startswith('_')
        or not isinstance(value, (list, tuple, GeneratorType))
    ):
        return False

    # If the group is a tuple of (hosts, data), check the hosts
    if isinstance(value, tuple):
        value = value[0]

    # Expand any generators of hosts
    if isinstance(value, GeneratorType):
        value = list(value)

    return all(
        isinstance(item, ALLOWED_HOST_TYPES)
        for item in value
    )


def is_group_data(key, value):
    '''
    Verify that a module-level variable (key = value) is a valid bit of group data.
    '''

    return (
        isinstance(value, ALLOWED_DATA_TYPES)
        and not key.startswith('_')
    )


def get_group_data(deploy_dir):
    group_data = {}
    group_data_directory = path.join(deploy_dir, 'group_data')

    if path.exists(group_data_directory):
        files = listdir(group_data_directory)

        for file in files:
            if not file.endswith('.py'):
                continue

            group_data_file = path.join(group_data_directory, file)
            group_name = path.basename(file)[:-3]

            logger.debug('Looking for group data in: {0}'.format(group_data_file))

            # Read the files locals into a dict
            attrs = exec_file(group_data_file, return_locals=True)

            group_data[group_name] = {
                key: value
                for key, value in six.iteritems(attrs)
                if is_group_data(key, value)
            }

    return group_data


def make_inventory(
    inventory_filename,
    deploy_dir=None, limit=None,
    ssh_user=None, ssh_key=None, ssh_key_password=None,
    ssh_port=None, ssh_password=None,
):
    '''
    Builds a ``pyinfra.api.Inventory`` from the filesystem. If the file does not exist
    and doesn't contain a / attempts to use that as the only hostname.
    '''

    if ssh_port is not None:
        ssh_port = int(ssh_port)

    file_groupname = None

    try:
        attrs = exec_file(inventory_filename, return_locals=True)

        groups = {
            key: value
            for key, value in six.iteritems(attrs)
            if is_inventory_group(key, value)
        }

        # Used to set all the hosts to an additional group - that of the filename
        # ie inventories/dev.py means all the hosts are in the dev group, if not present
        file_groupname = path.basename(inventory_filename).split('.')[0]

    except IOError:
        # Otherwise we assume the inventory is actually a hostname or list of hostnames
        groups = {
            'all': inventory_filename.split(','),
        }

    all_data = {}

    if 'all' in groups:
        all_hosts = groups.pop('all')

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

    groups['all'] = (all_hosts, all_data)

    # Apply the filename group if not already defined
    if file_groupname and file_groupname not in groups:
        groups[file_groupname] = all_hosts

    # In pyinfra an inventory is a combination of (hostnames + data). However, in CLI
    # mode we want to be define this in separate files (inventory / group data). The
    # issue is we want inventory access within the group data files - but at this point
    # we're not ready to make an Inventory. So here we just create a fake one, and
    # attach it to pseudo_inventory while we import the data files.
    logger.debug('Creating fake inventory...')

    fake_groups = {
        # In API mode groups *must* be tuples of (hostnames, data)
        name: group if isinstance(group, tuple) else (group, {})
        for name, group in six.iteritems(groups)
    }
    fake_inventory = Inventory((all_hosts, all_data), **fake_groups)
    pseudo_inventory.set(fake_inventory)

    # Get all group data (group_data/*.py)
    group_data = get_group_data(deploy_dir)

    # Reset the pseudo inventory
    pseudo_inventory.reset()

    # For each group load up any data
    for name, hosts in six.iteritems(groups):
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
    for name, data in six.iteritems(group_data):
        groups[name] = ([], data)

    # Apply any limit to all_hosts
    if limit:
        # Limits can be groups
        limit_groupname = limit
        if limit_groupname in groups:
            all_hosts = [
                host[0] if isinstance(host, tuple) else host
                for host in groups[limit_groupname][0]
            ]

        # Or hostnames w/*wildcards
        else:
            limits = limit.split(',')

            all_hosts = [
                host for host in all_hosts
                if (
                    isinstance(host, tuple)
                    and any(fnmatch(host[0], limit) for limit in limits)
                )
                or (
                    isinstance(host, six.string_types)
                    and any(fnmatch(host, limit) for limit in limits)
                )
            ]

        # Reassign the all group w/limit
        groups['all'] = (all_hosts, all_data)

    return Inventory(
        groups.pop('all'),
        ssh_user=ssh_user,
        ssh_key=ssh_key,
        ssh_key_password=ssh_key_password,
        ssh_port=ssh_port,
        ssh_password=ssh_password,
        **groups
    ), file_groupname and file_groupname.lower()
