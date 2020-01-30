'''
The pyinfra facts API. Facts enable pyinfra to collect remote server state which
is used to "diff" with the desired state, producing the final commands required
for a deploy.
'''

from __future__ import division, unicode_literals

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
from pyinfra.api.util import (
    get_arg_value,
    log_host_command_error,
    make_hash,
    underscore,
)
from pyinfra.progress import progress_spinner


# Index of snake_case facts -> CamelCase classes
FACTS = {}
FACT_LOCK = BoundedSemaphore()


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


def get_facts(state, name, args=None, ensure_hosts=None):
    '''
    Get a single fact for all hosts in the state.
    '''

    # Create an instance of the fact
    fact = get_fact_class(name)()

    if isinstance(fact, ShortFactBase):
        return get_short_facts(state, fact, args=args, ensure_hosts=ensure_hosts)

    logger.debug('Getting fact: {0} (ensure_hosts: {1})'.format(
        name, ensure_hosts,
    ))

    args = args or []

    # Apply args or defaults
    sudo = state.config.SUDO
    sudo_user = state.config.SUDO_USER
    su_user = state.config.SU_USER
    ignore_errors = state.config.IGNORE_ERRORS

    # Timeout for operations !== timeout for connect (config.CONNECT_TIMEOUT)
    timeout = None

    # Get the current op meta
    current_op_hash = state.current_op_hash
    current_op_meta = state.op_meta.get(current_op_hash)

    # If inside an operation, fetch config meta
    if current_op_meta:
        sudo = current_op_meta['sudo']
        sudo_user = current_op_meta['sudo_user']
        su_user = current_op_meta['su_user']
        ignore_errors = current_op_meta['ignore_errors']
        timeout = current_op_meta['timeout']

    # Make a hash which keeps facts unique - but usable cross-deploy/threads.
    # Locks are used to maintain order.
    fact_hash = make_hash((name, args, sudo, sudo_user, su_user, ignore_errors))

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
        hosts = set(state.inventory)
        if ensure_hosts:
            hosts.update(ensure_hosts)

        # Execute the command for each state inventory in a greenlet
        greenlet_to_host = {}

        for host in hosts:
            if host in current_facts:
                continue

            # if host in state.ready_hosts:
            #     continue

            # Work out the command
            command = fact.command

            if callable(command):
                # Generate actual arguments by passing strings as jinja2 templates
                host_args = [get_arg_value(state, host, arg) for arg in args]

                command = command(*host_args)

            greenlet = state.fact_pool.spawn(
                host.run_shell_command, state, command,
                sudo=sudo, sudo_user=sudo_user,
                su_user=su_user, timeout=timeout,
                print_output=state.print_fact_output,
                print_input=state.print_fact_input,
            )
            greenlet_to_host[greenlet] = host

        # Wait for all the commands to execute
        progress_prefix = 'fact: {0}'.format(name)
        if args:
            progress_prefix = '{0}{1}'.format(progress_prefix, args)

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
                status, stdout, _ = greenlet.get()

            except (timeout_error, socket_error, SSHException) as e:
                failed_hosts.add(host)
                log_host_command_error(
                    host, e,
                    timeout=timeout,
                )

            data = fact.default()

            if status and stdout:
                data = fact.process(stdout)

            hostname_facts[host] = data

        log_name = click.style(name, bold=True)

        filtered_args = list(filter(None, args))
        if filtered_args:
            log = 'Loaded fact {0}: {1}'.format(log_name, tuple(filtered_args))
        else:
            log = 'Loaded fact {0}'.format(log_name)

        if state.print_fact_info:
            logger.info(log)
        else:
            logger.debug(log)

        # Check we've not failed
        if not ignore_errors:
            state.fail_hosts(failed_hosts)

        # Assign the facts
        state.facts.setdefault(fact_hash, {}).update(hostname_facts)

    return state.facts[fact_hash]


def get_fact(state, host, name):
    '''
    Wrapper around ``get_facts`` returning facts for one host or a function
    that does.
    '''

    # Expecting a function to return
    if callable(getattr(FACTS[name], 'command', None)):
        def wrapper(*args):
            fact_data = get_facts(state, name, args=args, ensure_hosts=(host,))

            return fact_data.get(host)
        return wrapper

    # Expecting the fact as a return value
    else:
        # Get the fact
        fact_data = get_facts(state, name, ensure_hosts=(host,))

        return fact_data.get(host)
