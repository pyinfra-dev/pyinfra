from __future__ import unicode_literals

import click

from pyinfra import logger

from .connectors import EXECUTION_CONNECTORS
from .connectors.util import remove_any_sudo_askpass_file
from .exceptions import ConnectError, PyinfraError
from .facts import (
    create_host_fact,
    delete_host_fact,
    get_fact_class,
    get_fact_names,
    get_host_fact,
    is_fact,
)


# TODO: remove this! COMPAT w/<2
# This is the old-style `host.fact.<snake_case_name>` "magic" fact attributes
# which have been replaced by the much cleaner `host.get_fact(fact_cls, *args, **kwargs)`.
class HostFacts(object):
    def __init__(self, host=None):
        self.host = host

    def __dir__(self):
        return get_fact_names()

    def _check_host(self):
        if not self.host:
            raise TypeError('Cannot call this function with no host!')

    def __getattr__(self, key):
        self._check_host()

        if not is_fact(key):
            raise AttributeError('No such fact: {0}'.format(key))

        # Ensure this host is connected
        connection = self.host.connect(reason='for {0} fact'.format(key))

        # If we can't connect - fail immediately as we specifically need this
        # fact for this host and without it we cannot satisfy the deploy.
        if not connection:
            raise PyinfraError('Could not connect to {0} for fact {1}!'.format(
                self.host, key,
            ))

        # Expecting a function to return
        if callable(getattr(get_fact_class(key), 'command', None)):
            def wrapper(*args, **kwargs):
                return get_host_fact(self.host.state, self.host, key, args=args, kwargs=kwargs)
            return wrapper

        # Expecting the fact as a return value
        else:
            return get_host_fact(self.host.state, self.host, key)

    def _create(self, key, data=None, args=None):
        self._check_host()
        return create_host_fact(self.host.state, self.host, key, data, args)

    def _delete(self, key, args=None):
        self._check_host()
        return delete_host_fact(self.host.state, self.host, key, args)


class Host(object):
    '''
    Represents a target host. Thin class that links up to facts and host/group
    data.
    '''

    connection = None
    state = None
    fact = HostFacts()  # this isn't usable, but provides support for dir()

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
        self.fact = HostFacts(self)

        # Arbitrary dict for connector use
        self.connector_data = {}

    def __str__(self):
        return '{0}'.format(self.name)

    def __repr__(self):
        return 'Host({0})'.format(self.name)

    @property
    def connected(self):
        return self.connection is not None

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

    def noop(self, description):
        '''
        Log a description for a noop operation.
        '''

        handler = logger.info if self.state.print_noop_info else logger.debug
        handler('{0}noop: {1}'.format(self.print_prefix, description))

    # Host facts
    #

    def get_fact(self, name_or_cls, *args, **kwargs):
        return get_host_fact(self.state, self, name_or_cls, args, kwargs)

    def create_fact(self, name_or_cls, data=None, args=None):
        return create_host_fact(self.state, self, name_or_cls, data, args)

    def delete_fact(self, name_or_cls, args=None):
        return delete_host_fact(self.state, self, name_or_cls, args)

    # Connector proxy
    #

    def _check_state(self):
        if not self.state:
            raise TypeError('Cannot call this function with no state!')

    def connect(self, reason=None, show_errors=True):
        self._check_state()
        if not self.connection:
            self.state.trigger_callbacks('host_before_connect', self)

            try:
                self.connection = self.executor.connect(self.state, self)
            except ConnectError as e:
                if show_errors:
                    log_message = '{0}{1}'.format(
                        self.print_prefix,
                        click.style(e.args[0], 'red'),
                    )
                    logger.error(log_message)

                self.state.trigger_callbacks('host_connect_error', self, e)
            else:
                log_message = '{0}{1}'.format(
                    self.print_prefix,
                    click.style('Connected', 'green'),
                )
                if reason:
                    log_message = '{0}{1}'.format(
                        log_message,
                        ' ({0})'.format(reason),
                    )

                logger.info(log_message)
                self.state.trigger_callbacks('host_connect', self)

        return self.connection

    def disconnect(self):
        self._check_state()

        # Disconnect is an optional function for executors if needed
        disconnect_func = getattr(self.executor, 'disconnect', None)
        if disconnect_func:
            return disconnect_func(self.state, self)

        # TODO: consider whether this should be here!
        remove_any_sudo_askpass_file(self)

        self.state.trigger_callbacks('host_disconnect', self)

    def run_shell_command(self, *args, **kwargs):
        self._check_state()
        return self.executor.run_shell_command(self.state, self, *args, **kwargs)

    def put_file(self, *args, **kwargs):
        self._check_state()
        return self.executor.put_file(self.state, self, *args, **kwargs)

    def get_file(self, *args, **kwargs):
        self._check_state()
        return self.executor.get_file(self.state, self, *args, **kwargs)

    # Rsync - optional executor specific ability

    def check_can_rsync(self):
        check_can_rsync_func = getattr(self.executor, 'check_can_rsync', None)
        if check_can_rsync_func:
            return check_can_rsync_func(self)

        raise NotImplementedError('The {0} connector does not support rsync!'.format(
            self.executor.__name__,
        ))

    def rsync(self, *args, **kwargs):
        self._check_state()
        return self.executor.rsync(self.state, self, *args, **kwargs)
