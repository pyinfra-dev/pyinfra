from contextlib import contextmanager

import click
from gevent.lock import BoundedSemaphore

from pyinfra import logger
from pyinfra.connectors.util import remove_any_sudo_askpass_file

from .connectors import get_execution_connector
from .exceptions import ConnectError
from .facts import create_host_fact, delete_host_fact, get_host_fact, reload_host_fact


def extract_callable_datas(datas):
    for data in datas:
        # Support for dynamic data, ie @deploy wrapped data defaults where
        # the data is stored on the state temporarily.
        if callable(data):
            data = data()

        yield data


class HostData(object):
    """
    Combines multiple AttrData's to search for attributes.
    """

    override_datas = None

    def __init__(self, host, *datas):
        self.__dict__["host"] = host

        datas = list(datas)

        # Inject an empty override data so we can assign during deploy
        self.__dict__["override_datas"] = {}
        datas.insert(0, self.override_datas)

        self.__dict__["datas"] = tuple(datas)

    def __getattr__(self, key):
        for data in extract_callable_datas(self.datas):
            try:
                return data[key]
            except KeyError:
                pass

        raise AttributeError(f"Host `{self.host}` has no data `{key}`")

    def __setattr__(self, key, value):
        self.override_datas[key] = value

    def __str__(self):
        return str(self.datas)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def dict(self):
        out = {}

        # Copy and reverse data objects (such that the first items override
        # the last, matching __getattr__ output).
        datas = list(self.datas)
        datas.reverse()

        for data in extract_callable_datas(datas):
            out.update(data)

        return out


class Host(object):
    """
    Represents a target host. Thin class that links up to facts and host/group
    data.
    """

    connection = None
    state = None

    # Current context inside an @operation function (op gen stage)
    in_op = False
    current_op_hash = None
    current_op_global_kwargs = None

    # Current context inside a @deploy function (op gen stage)
    in_deploy = False
    current_deploy_name = None
    current_deploy_kwargs = None
    current_deploy_data = None
    current_deploy_op_order = None

    # Current context during operation execution
    executing_op_hash = None
    nested_executing_op_hash = None

    def __init__(
        self,
        name,
        inventory,
        groups,
        executor=get_execution_connector("ssh"),
    ):
        self.inventory = inventory
        self.groups = groups
        self.executor = executor
        self.name = name

        # Arbitrary dict for connector use
        self.connector_data = {}

        # Fact data store
        self.facts = {}
        self.facts_lock = BoundedSemaphore()

        # Create the (waterfall data: override, host, group, global)
        self.data = HostData(
            self,
            lambda: inventory.get_override_data(),
            lambda: inventory.get_host_data(name),
            lambda: inventory.get_groups_data(groups),
            lambda: inventory.get_data(),
            # @deploy function data are default values, so come last
            self.get_deploy_data,
        )

    def __str__(self):
        return "{0}".format(self.name)

    def __repr__(self):
        return "Host({0})".format(self.name)

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
        if self.nested_executing_op_hash:
            return "{0}[{1}] {2} ".format(
                click.style(""),  # reset
                click.style(self.name, bold=True),
                click.style("nested", "blue"),
            )

        return "{0}[{1}] ".format(
            click.style(""),  # reset
            click.style(self.name, bold=True),
        )

    def style_print_prefix(self, *args, **kwargs):
        return "{0}[{1}] ".format(
            click.style(""),  # reset
            click.style(self.name, *args, **kwargs),
        )

    def get_deploy_data(self):
        if self.current_deploy_data:
            return self.current_deploy_data

        return {}

    def noop(self, description):
        """
        Log a description for a noop operation.
        """

        handler = logger.info if self.state.print_noop_info else logger.debug
        handler("{0}noop: {1}".format(self.print_prefix, description))

    @contextmanager
    def deploy(self, name, kwargs, data, in_deploy=True, deploy_op_order=None):
        """
        Wraps a group of operations as a deploy, this should not be used
        directly, instead use ``pyinfra.api.deploy.deploy``.
        """

        # Handle nested deploy names
        if self.current_deploy_name:
            name = "{0} | {1}".format(self.current_deploy_name, name)

        # Store the previous values
        old_in_deploy = self.in_deploy
        old_deploy_name = self.current_deploy_name
        old_deploy_kwargs = self.current_deploy_kwargs
        old_deploy_data = self.current_deploy_data
        old_deploy_op_order = self.current_deploy_op_order
        self.in_deploy = in_deploy

        # Set the new values
        self.current_deploy_name = name
        self.current_deploy_kwargs = kwargs
        self.current_deploy_data = data
        self.current_deploy_op_order = deploy_op_order
        logger.debug(
            "Starting deploy {0} (args={1}, data={2})".format(
                name,
                kwargs,
                data,
            ),
        )

        yield

        # Restore the previous values
        self.in_deploy = old_in_deploy
        self.current_deploy_name = old_deploy_name
        self.current_deploy_kwargs = old_deploy_kwargs
        self.current_deploy_data = old_deploy_data
        self.current_deploy_op_order = old_deploy_op_order

        logger.debug(
            "Reset deploy to {0} (args={1}, data={2})".format(
                old_deploy_name,
                old_deploy_kwargs,
                old_deploy_data,
            ),
        )

    # Host facts
    #

    def get_fact(self, name_or_cls, *args, **kwargs):
        return get_host_fact(self.state, self, name_or_cls, args=args, kwargs=kwargs)

    def reload_fact(self, name_or_cls, *args, **kwargs):
        return reload_host_fact(self.state, self, name_or_cls, args=args, kwargs=kwargs)

    def create_fact(self, name_or_cls, data=None, kwargs=None):
        return create_host_fact(self.state, self, name_or_cls, data, kwargs=kwargs)

    def delete_fact(self, name_or_cls, kwargs=None):
        return delete_host_fact(self.state, self, name_or_cls, kwargs=kwargs)

    # Connector proxy
    #

    def _check_state(self):
        if not self.state:
            raise TypeError("Cannot call this function with no state!")

    def connect(self, reason=None, show_errors=True, raise_exceptions=False):
        self._check_state()
        if not self.connection:
            self.state.trigger_callbacks("host_before_connect", self)

            try:
                self.connection = self.executor.connect(self.state, self)
            except ConnectError as e:
                if show_errors:
                    log_message = "{0}{1}".format(
                        self.print_prefix,
                        click.style(e.args[0], "red"),
                    )
                    logger.error(log_message)

                self.state.trigger_callbacks("host_connect_error", self, e)

                if raise_exceptions:
                    raise
            else:
                log_message = "{0}{1}".format(
                    self.print_prefix,
                    click.style("Connected", "green"),
                )
                if reason:
                    log_message = "{0}{1}".format(
                        log_message,
                        " ({0})".format(reason),
                    )

                logger.info(log_message)
                self.state.trigger_callbacks("host_connect", self)

        return self.connection

    def disconnect(self):
        self._check_state()

        # Disconnect is an optional function for executors if needed
        disconnect_func = getattr(self.executor, "disconnect", None)
        if disconnect_func:
            return disconnect_func(self.state, self)

        # TODO: consider whether this should be here!
        remove_any_sudo_askpass_file(self)

        self.state.trigger_callbacks("host_disconnect", self)

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
        check_can_rsync_func = getattr(self.executor, "check_can_rsync", None)
        if check_can_rsync_func:
            return check_can_rsync_func(self)

        raise NotImplementedError(
            "The {0} connector does not support rsync!".format(
                self.executor.__name__,
            ),
        )

    def rsync(self, *args, **kwargs):
        self._check_state()
        return self.executor.rsync(self.state, self, *args, **kwargs)
