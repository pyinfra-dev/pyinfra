# pyinfra
# File: pyinfra/api/inventory.py
# Desc: represents a pyinfra inventory

import six

from .host import Host
from .attrs import AttrData


class Inventory(object):
    '''
    Represents a collection of target hosts. Stores and provides access to group data,
    host data and default data for these hosts.

    Args:
        names_data: tuple of ``(names, data)``
        ssh_user: default SSH user
        ssh_port: default SSH port
        ssh_key: default SSH key filename
        ssh_key_password: default password for the SSH key
        ssh_password: default SSH password
        **groups: map of group names -> ``(names, data)``
    '''

    state = None

    def __init__(
        self, names_data,
        ssh_user=None, ssh_port=None, ssh_key=None,
        ssh_key_password=None, ssh_password=None, **groups
    ):
        names, data = names_data

        self.connected_hosts = set()
        self.groups = {}
        self.host_data = {}
        self.group_data = {}

        # In CLI mode these are --user, --key, etc
        override_data = {
            'ssh_user': ssh_user,
            'ssh_key': ssh_key,
            'ssh_key_password': ssh_key_password,
            'ssh_port': ssh_port,
            'ssh_password': ssh_password
        }
        # Strip None values
        override_data = {
            key: value
            for key, value in six.iteritems(override_data)
            if value is not None
        }

        self.override_data = AttrData(override_data)

        self.data = AttrData(data)

        # Build host data
        for name in names:
            if isinstance(name, tuple):
                self.host_data[name[0]] = name[1]
            else:
                self.host_data[name] = {}

        # Loop groups and build map of name -> groups
        names_to_groups = {}
        for group_name, (group_names, group_data) in six.iteritems(groups):
            group_name = group_name.lower()
            self.group_data[group_name] = AttrData(group_data)

            for name in group_names:
                # Extract any data
                if isinstance(name, tuple):
                    self.host_data.setdefault(name[0], {}).update(name[1])
                    name = name[0]

                names_to_groups.setdefault(name, []).append(group_name)

        # Now we've got host data, convert -> AttrData
        self.host_data = {
            name: AttrData(d)
            for name, d in six.iteritems(self.host_data)
        }

        # Actually make Host instances
        hosts = {}
        for name in names:
            name = name[0] if isinstance(name, tuple) else name

            # Create the Host
            host = Host(self, name, names_to_groups.get(name))
            hosts[name] = host

            # Push into any groups
            for groupname in names_to_groups.get(name, []):
                self.groups.setdefault(groupname, []).append(host)

        self.hosts = hosts

    def __getitem__(self, key):
        '''
        Get individual hosts from the inventory by name.
        '''

        return self.hosts.get(key)

    def __getattr__(self, key):
        '''
        Get groups (lists of hosts) from the inventory by name.
        '''

        return self.groups.get(key)

    def __len__(self):
        '''
        Returns a list of all hosts, connected or not.
        '''

        return len(self.hosts)

    def __iter__(self):
        '''
        Iterates over inventory hosts. Uses active hosts only when they exist - in that
        sense can be seen as the "active" list of hosts during a deploy.
        '''

        for host in self.hosts.values():
            if not self.active_hosts:
                yield host

            elif host.name in self.active_hosts:
                yield host

    def get_data(self):
        '''
        Get the base/all data attached to this inventory.
        '''

        return self.data

    def get_override_data(self):
        '''
        Get override data for this inventory.
        '''

        return self.override_data

    def get_host_data(self, hostname):
        '''
        Get data for a single host in this inventory.
        '''

        return self.host_data[hostname]

    def get_group_data(self, group):
        '''
        Get data for a single group in this inventory.
        '''

        return self.group_data.get(group, {})

    def get_groups_data(self, groups):
        '''
        Gets aggregated data from a list of groups. Vars are collected in order so, for
        any groups which define the same var twice, the last group's value will hold.
        '''

        data = {}

        for group in groups:
            data.update(
                self.get_group_data(group).dict()
            )

        return AttrData(data)
