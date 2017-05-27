# pyinfra
# File: pyinfra/api/host.py
# Desc: thin class that represents a target host in pyinfra

from __future__ import unicode_literals

import click

from .attrs import FallbackAttrData, wrap_attr_data
from .connectors import local, ssh
from .facts import get_fact, is_fact


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

    connection = None

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
            inventory.get_data(),
        )

        # Attach the fact structure
        self.fact = HostFacts(inventory, name)

        # Work out the connector
        connector = ssh
        hostname = self.data.ssh_hostname or name

        if hostname == '@local':
            connector = local

        self.connector = connector

    @property
    def host_data(self):
        return self.inventory.get_host_data(self.name)

    @property
    def group_data(self):
        return self.inventory.get_groups_data(self.groups)

    @property
    def print_prefix(self):
        return '[{0}] '.format(click.style(self.name, bold=True))

    # Connector proxy
    #

    def connect(self, state, *args, **kwargs):
        self.connection = self.connector.connect(state, self, *args, **kwargs)
        return self.connection

    def run_shell_command(self, state, *args, **kwargs):
        return self.connector.run_shell_command(state, self, *args, **kwargs)

    def put_file(self, state, *args, **kwargs):
        return self.connector.put_file(state, self, *args, **kwargs)
