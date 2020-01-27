from __future__ import unicode_literals

import click

from pyinfra import logger

from .connectors import EXECUTION_CONNECTORS
from .exceptions import ConnectError, PyinfraError
from .facts import get_fact, is_fact


class HostFacts(object):
    def __init__(self, inventory, host):
        self.inventory = inventory
        self.host = host

    def __getattr__(self, key):
        if not is_fact(key):
            raise AttributeError('No such fact: {0}'.format(key))

        # Ensure this host is connected
        connection = self.host.connect(self.inventory.state, for_fact=key)

        # If we can't connect - fail immediately as we specifically need this
        # fact for this host and without it we cannot satisfy the deploy.
        if not connection:
            raise PyinfraError('Could not connect to {0} for fact {1}!'.format(
                self.host, key,
            ))

        return get_fact(self.inventory.state, self.host, key)


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
        self.groups = groups
        self.data = data
        self.executor = executor
        self.name = name

        # Attach the fact proxy
        self.fact = HostFacts(inventory, self)

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

    def connect(self, state, for_fact=None, show_errors=True):
        if not self.connection:
            try:
                self.connection = self.executor.connect(state, self)
            except ConnectError as e:
                if show_errors:
                    log_message = '{0}{1}'.format(
                        self.print_prefix,
                        click.style(e.args[0], 'red'),
                    )
                    logger.error(log_message)
            else:
                log_message = '{0}{1}'.format(
                    self.print_prefix,
                    click.style('Connected', 'green'),
                )
                if for_fact:
                    log_message = '{0}{1}'.format(
                        log_message,
                        ' (for {0} fact)'.format(for_fact),
                    )

                logger.info(log_message)

        return self.connection

    def disconnect(self, state):
        # Disconnect is an optional function for executors if needed
        disconnect_func = getattr(self.executor, 'disconnect', None)
        if disconnect_func:
            return disconnect_func(state, self)

    def run_shell_command(self, state, *args, **kwargs):
        return self.executor.run_shell_command(state, self, *args, **kwargs)

    def put_file(self, state, *args, **kwargs):
        return self.executor.put_file(state, self, *args, **kwargs)

    def get_file(self, state, *args, **kwargs):
        return self.executor.get_file(state, self, *args, **kwargs)
