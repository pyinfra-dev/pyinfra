# pyinfra
# File: pyinfra/api/inventory.py
# Desc: represents a pyinfra inventory

from .host import Host
from .attrs import AttrData


class Inventory(object):
    '''
    Represents a collection of target hosts. Stores and provides access too group data,
    host data and default data for these hosts.
    '''
    def __init__(
        self, hostnames_data,
        ssh_user=None, ssh_key=None, ssh_key_password=None, ssh_port=None, **kwargs
    ):
        hostnames, data = hostnames_data

        self.connected_hosts = set()
        self.host_data = {}
        self.group_data = {}

        # THIS STUFF (--user, --key, --port)/api-shortcut SHOULD OVERRIDE BELOW
        # so no default, but update data before -> AttrData
        self.default_data = AttrData({
            'ssh_user': ssh_user,
            'ssh_key': ssh_key,
            'ssh_key_password': ssh_key_password,
            'ssh_port': ssh_port or 22
        })

        self.data = AttrData(data)

        # Loop groups and build map of hostnames -> groups
        hostnames_to_groups = {}
        for group_name, (group_hostnames, group_data) in kwargs.iteritems():
            group_name = group_name.lower()
            self.group_data[group_name] = AttrData(group_data)

            for hostname in group_hostnames:
                hostname = hostname[0] if isinstance(hostname, tuple) else hostname
                hostnames_to_groups.setdefault(hostname, []).append(group_name)

        # Build the actual Host instances
        hosts = {}
        for hostname in hostnames:
            host_data = {}
            if isinstance(hostname, tuple):
                hostname, host_data = hostname

            self.host_data[hostname] = AttrData(host_data)

            hosts[hostname] = Host(hostname, hostnames_to_groups.get(hostname))

        self.hosts = hosts

    def __getitem__(self, key):
        return self.hosts.get(key)

    def __len__(self):
        return len(self.hosts)

    def __iter__(self):
        for host in self.hosts.values():
            if not self.connected_hosts:
                yield host
            elif host.ssh_hostname in self.connected_hosts:
                yield host

    def get_data(self):
        return self.data

    def get_default_data(self):
        return self.default_data

    def get_host_data(self, hostname):
        return self.host_data[hostname]

    def get_group_data(self, group):
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
