# pyinfra
# File: pyinfra/api/host.py
# Desc: thin class that represents a target host in pyinfra

from __future__ import unicode_literals

import click

from .attrs import wrap_attr_data
from .connectors import EXECUTION_CONNECTORS
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
    Represents a target host. Thin class that links up to facts and host/group
    data.
    '''

    connection = None

    def __init__(
        self, name, inventory, groups, data,
        executor=EXECUTION_CONNECTORS['ssh'],
    ):
        self.inventory = inventory
        self.name = name
        self.groups = groups
        self.data = data
        self.executor = executor

        # Attach the fact proxy
        self.fact = HostFacts(inventory, name)

    def __repr__(self):
        return self.name

    @property
    def host_data(self):
        return self.inventory.get_host_data(self.name)

    @property
    def group_data(self):
        return self.inventory.get_groups_data(self.groups)

    @property
    def print_prefix(self):
        return '{0}[{1}] '.format(
            click.style(''),  # reset
            click.style(self.name, bold=True),
        )

    def style_print_prefix(self, *args, **kwargs):
        return '{0}[{1}] '.format(
            click.style(''),  # reset
            click.style(self.name, *args, **kwargs),
        )

    # Connector proxy
    #

    def connect(self, state, *args, **kwargs):
        if not self.connection:
            self.connection = self.executor.connect(state, self, *args, **kwargs)

        return self.connection

    def run_shell_command(self, state, *args, **kwargs):
        return self.executor.run_shell_command(state, self, *args, **kwargs)

    def put_file(self, state, *args, **kwargs):
        return self.executor.put_file(state, self, *args, **kwargs)
