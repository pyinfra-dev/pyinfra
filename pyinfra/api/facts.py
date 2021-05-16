'''
The pyinfra facts API. Facts enable pyinfra to collect remote server state which
is used to "diff" with the desired state, producing the final commands required
for a deploy.
'''

from __future__ import division, unicode_literals

import re

from inspect import getcallargs, isclass
from socket import (
    error as socket_error,
    timeout as timeout_error,
)

import click
import gevent
import six

from gevent.lock import BoundedSemaphore
from paramiko import SSHException

from pyinfra import logger
from pyinfra.api import StringCommand
from pyinfra.api.connectors.util import split_combined_output
from pyinfra.api.util import (
    get_arg_value,
    get_kwargs_str,
    log_error_or_warning,
    log_host_command_error,
    make_hash,
    print_host_combined_output,
    underscore,
)
from pyinfra.progress import progress_spinner

from .operation_kwargs import get_executor_kwarg_keys


# Index of snake_case facts -> CamelCase classes
FACTS = {}
FACT_LOCK = BoundedSemaphore()

SUDO_REGEX = r'^sudo: unknown user:'
SU_REGEXES = (
    r'^su: user .+ does not exist',
    r'^su: unknown login',
)


def is_fact(name):
    return name in FACTS


def get_fact_class(name):
    return FACTS[name]


def get_fact_names():
    '''
    Returns a list of available facts in camel_case format.
    '''

    return list(six.iterkeys(FACTS))


class FactMeta(type):
    '''
    Metaclass to dynamically build the facts index.
    '''

    def __init__(cls, name, bases, attrs):
        if attrs.get('abstract'):
            return

        fact_name = underscore(name)
        cls.name = fact_name

        # Get the an instance of the fact, attach to facts
        FACTS[fact_name] = cls


@six.add_metaclass(FactMeta)
class FactBase(object):
    abstract = True

    shell_executable = None

    requires_command = None

    @staticmethod
    def default():
        '''
        Set the default attribute to be a type (eg list/dict).
        '''

    @staticmethod
    def process(output):
        return '\n'.join(output)

    def process_pipeline(self, args, output):
        return {
            arg: self.process([output[i]])
            for i, arg in enumerate(args)
        }


@six.add_metaclass(FactMeta)
class ShortFactBase(object):
    fact = None


def get_short_facts(state, short_fact, **kwargs):
    facts = get_facts(state, short_fact.fact.name, **kwargs)

    return {
        host: short_fact.process_data(data)
        for host, data in six.iteritems(facts)
    }


def _make_command(command_attribute, host_args):
    if callable(command_attribute):
        host_args.pop('self', None)
        return command_attribute(**host_args)
    return command_attribute


def get_facts(
    state,
    name_or_cls,
    args=None,
    kwargs=None,
    ensure_hosts=None,
    apply_failed_hosts=True,
):
    '''
    Get a single fact for all hosts in the state.
    '''

    # TODO: tidy up the whole executor argument handling here!
    global_kwarg_overrides = {}
    if kwargs:
        global_kwarg_overrides.update({
            key: kwargs.pop(key)
            for key in get_executor_kwarg_keys()
            if key in kwargs
        })

    if isclass(name_or_cls) and issubclass(name_or_cls, (FactBase, ShortFactBase)):
        fact = name_or_cls()
        name = fact.name
    else:
        fact = get_fact_class(name_or_cls)()
        name = name_or_cls

    if isinstance(fact, ShortFactBase):
        return get_short_facts(state, fact, args=args, ensure_hosts=ensure_hosts)

    args = args or ()
    kwargs = kwargs or {}
    if args or kwargs:
        # Merges args & kwargs into a single kwargs dictionary
        kwargs = getcallargs(fact.command, *args, **kwargs)

    logger.debug('Getting fact: {0} {1} (ensure_hosts: {2})'.format(
        name, get_kwargs_str(kwargs), ensure_hosts,
    ))

    # Apply args or defaults
    sudo = state.config.SUDO
    sudo_user = state.config.SUDO_USER
    su_user = state.config.SU_USER
    ignore_errors = state.config.IGNORE_ERRORS
    shell_executable = state.config.SHELL
    use_sudo_password = state.config.USE_SUDO_PASSWORD
    env = state.config.ENV

    # Facts can override the shell (winrm powershell vs cmd support)
    if fact.shell_executable:
        shell_executable = fact.shell_executable

    # Timeout for operations !== timeout for connect (config.CONNECT_TIMEOUT)
    timeout = None

    # If inside an operation, fetch global arguments
    current_global_kwargs = state.current_op_global_kwargs or {}
    # Allow `Host.get_fact` calls to explicitly override these
    current_global_kwargs.update(global_kwarg_overrides)
    if current_global_kwargs:
        sudo = current_global_kwargs.get('sudo', sudo)
        sudo_user = current_global_kwargs.get('sudo_user', sudo_user)
        use_sudo_password = current_global_kwargs.get('use_sudo_password', use_sudo_password)
        su_user = current_global_kwargs.get('su_user', su_user)
        ignore_errors = current_global_kwargs.get('ignore_errors', ignore_errors)
        timeout = current_global_kwargs.get('timeout', timeout)
        env = current_global_kwargs.get('env', env)

    # Make a hash which keeps facts unique - but usable cross-deploy/threads.
    # Locks are used to maintain order.
    fact_hash = make_hash((name, kwargs, sudo, sudo_user, su_user, ignore_errors, env))

    # Already got this fact? Unlock and return them
    current_facts = state.facts.get(fact_hash, {})
    if current_facts:
        if not ensure_hosts or all(
            host in current_facts for host in ensure_hosts
        ):
            return current_facts

    with FACT_LOCK:
        # Add any hosts we must have, whether considered in the inventory or not
        # (these hosts might be outside the --limit or current op limit_hosts).
        hosts = set(state.inventory.iter_active_hosts())
        if ensure_hosts:
            hosts.update(ensure_hosts)

        # Execute the command for each state inventory in a greenlet
        greenlet_to_host = {}

        for host in hosts:
            if host in current_facts:
                continue

            # Generate actual arguments by passing strings as jinja2 templates
            host_kwargs = {
                key: get_arg_value(state, host, arg)
                for key, arg in kwargs.items()
            }

            command = _make_command(fact.command, host_kwargs)
            requires_command = _make_command(fact.requires_command, host_kwargs)
            if requires_command:
                command = StringCommand(
                    # Command doesn't exist, return 0 *or* run & return fact command
                    '!', 'command', '-v', requires_command, '>/dev/null', '||', command,
                )

            greenlet = state.fact_pool.spawn(
                host.run_shell_command,
                command,
                sudo=sudo,
                sudo_user=sudo_user,
                use_sudo_password=use_sudo_password,
                su_user=su_user,
                timeout=timeout,
                env=env,
                shell_executable=shell_executable,
                print_output=state.print_fact_output,
                print_input=state.print_fact_input,
                return_combined_output=True,
            )
            greenlet_to_host[greenlet] = host

        # Wait for all the commands to execute
        progress_prefix = 'fact: {0} {1}'.format(name, get_kwargs_str(kwargs))

        with progress_spinner(
            greenlet_to_host.values(),
            prefix_message=progress_prefix,
        ) as progress:
            for greenlet in gevent.iwait(greenlet_to_host.keys()):
                host = greenlet_to_host[greenlet]
                progress(host)

        hostname_facts = {}
        failed_hosts = set()

        # Collect the facts and any failures
        for greenlet, host in six.iteritems(greenlet_to_host):
            status = False
            stdout = []

            try:
                status, combined_output_lines = greenlet.get()
            except (timeout_error, socket_error, SSHException) as e:
                failed_hosts.add(host)
                log_host_command_error(
                    host, e,
                    timeout=timeout,
                )

            stdout, stderr = split_combined_output(combined_output_lines)

            data = fact.default()

            if status:
                if stdout:
                    data = fact.process(stdout)

            elif stderr:
                first_line = stderr[0]
                if (
                    sudo_user
                    and state.will_add_user(sudo_user)
                    and re.match(SUDO_REGEX, first_line)
                ):
                    status = True
                if (
                    su_user
                    and state.will_add_user(su_user)
                    and any(re.match(regex, first_line) for regex in SU_REGEXES)
                ):
                    status = True

            if not status:
                failed_hosts.add(host)

                if not state.print_fact_output:
                    print_host_combined_output(host, combined_output_lines)

                log_error_or_warning(host, ignore_errors, description=(
                    'could not load fact: {0} {1}'
                ).format(name, get_kwargs_str(kwargs)))

            hostname_facts[host] = data

        log = 'Loaded fact {0} {1}'.format(click.style(name, bold=True), get_kwargs_str(kwargs))
        if state.print_fact_info:
            logger.info(log)
        else:
            logger.debug(log)

        # Check we've not failed
        if not ignore_errors and apply_failed_hosts:
            state.fail_hosts(failed_hosts)

        # Assign the facts
        state.facts.setdefault(fact_hash, {}).update(hostname_facts)

    return state.facts[fact_hash]


def get_host_fact(state, host, name, args=None, kwargs=None):
    fact_data = get_facts(state, name, args=args, kwargs=kwargs, ensure_hosts=(host,))
    return fact_data.get(host)


def create_host_fact(state, host, name, data, args=None):
    fact_data = get_facts(state, name, args=args, ensure_hosts=(host,))
    fact_data[host] = data


def delete_host_fact(state, host, name, args=None):
    fact_data = get_facts(state, name, args=args, ensure_hosts=(host,))
    fact_data.pop(host, None)
