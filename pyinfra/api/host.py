# pyinfra
# File: pyinfra/api/host.py
# Desc: thin class that represents a target host in pyinfra

from __future__ import unicode_literals

from .facts import is_fact, get_fact
from .attrs import FallbackAttrData, wrap_attr_data


class HostFacts(object):
    def __init__(self, inventory, name):
        self.inventory = inventory
        self.name = name

    def __getattr__(self, key):
        if not is_fact(key):
            raise AttributeError('No such fact: {0}'.format(key))

        fact = get_fact(self.inventory.state, self.name, key)
        return wrap_attr_data(key, fact)


class Host(object):
    '''
    Represents a target host. Thin class that links up to facts and host/group data.
    '''

    _data = None

    def __init__(self, inventory, name, groups=None):
        groups = groups if groups else []

        self.inventory = inventory
        self.name = name
        self.groups = groups

        # Attach the (override, default to: host, group, global) data structure
        self.data = FallbackAttrData(
            inventory.get_override_data(),
            inventory.get_host_data(name),
            inventory.get_groups_data(groups),
            inventory.get_data()
        )

        # Attach the fact structure
        self.fact = HostFacts(inventory, name)

    @property
    def host_data(self):
        return self.inventory.get_host_data(self.name)

    @property
    def group_data(self):
        return self.inventory.get_groups_data(self.groups)
