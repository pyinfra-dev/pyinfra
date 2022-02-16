'''
The pyinfra facts API. Facts enable pyinfra to collect remote server state which
is used to "diff" with the desired state, producing the final commands required
for a deploy.
'''

import re

from inspect import getcallargs, isclass
from socket import (
    error as socket_error,
    timeout as timeout_error,
)

import click
import gevent

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

from .arguments import get_executor_kwarg_keys


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

    return list(FACTS.keys())


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


class FactBase(object, metaclass=FactMeta):
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


class ShortFactBase(object, metaclass=FactMeta):
    fact = None


def get_short_facts(state, host, short_fact, **kwargs):
    facts = get_fact(state, host, short_fact.fact.name, **kwargs)

    return {
        host: short_fact.process_data(data)
        for host, data in facts.items()
    }


def _make_command(command_attribute, host_args):
    if callable(command_attribute):
        host_args.pop('self', None)
        return command_attribute(**host_args)
    return command_attribute


def _get_executor_kwargs(state, host):
    kwargs = {
        'sudo': state.config.SUDO,
        'sudo_user': state.config.SUDO_USER,
        'su_user': state.config.SU_USER,
        'shell_executable': state.config.SHELL,
        'use_sudo_password': state.config.USE_SUDO_PASSWORD,
        'env': state.config.ENV,
        'timeout': None,
    }

    current_global_kwargs = host.current_op_global_kwargs or {}
    executor_kwarg_keys = get_executor_kwarg_keys()
    kwargs.update({
        key: current_global_kwargs[key]
        for key in executor_kwarg_keys
        if key in current_global_kwargs
    })

    return kwargs


def get_facts(state, *args, **kwargs):
    greenlet_to_host = {
        state.pool.spawn(get_fact, state, host, *args, **kwargs): host
        for host in state.inventory.iter_active_hosts()
    }

    results = {}

    with progress_spinner(greenlet_to_host.values()) as progress:
        for greenlet in gevent.iwait(greenlet_to_host.keys()):
            host = greenlet_to_host[greenlet]
            results[host] = greenlet.get()
            progress(host)

    return results


def get_fact(
    state,
    host,
    name_or_cls,
    args=None,
    kwargs=None,
    ensure_hosts=None,
    apply_failed_hosts=True,
    fact_hash=None,
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
        return get_short_facts(state, host, fact, args=args, ensure_hosts=ensure_hosts)

    # Apply args or defaults
    executor_kwargs = _get_executor_kwargs(state, host)

    args = args or ()
    kwargs = kwargs or {}
    if args or kwargs:
        # Merges args & kwargs into a single kwargs dictionary
        kwargs = getcallargs(fact.command, *args, **kwargs)

    logger.debug('Getting fact: {0} ({1}) (ensure_hosts: {2})'.format(
        name, get_kwargs_str(kwargs), ensure_hosts,
    ))

    ignore_errors = (host.current_op_global_kwargs or {}).get(
        'ignore_errors',
        state.config.IGNORE_ERRORS,
    )

    # Facts can override the shell (winrm powershell vs cmd support)
    if fact.shell_executable:
        executor_kwargs['shell_executable'] = fact.shell_executable

    # Already got this fact? Unlock and return them
    if fact_hash:
        current_fact = host.facts.get(fact_hash)
        if current_fact:
            return current_fact

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

    status = False
    stdout = []

    try:
        status, combined_output_lines = host.run_shell_command(
            command,
            print_output=state.print_fact_output,
            print_input=state.print_fact_input,
            return_combined_output=True,
            **executor_kwargs,
        )
    except (timeout_error, socket_error, SSHException) as e:
        log_host_command_error(
            host, e,
            timeout=executor_kwargs['timeout'],
        )

    stdout, stderr = split_combined_output(combined_output_lines)

    data = fact.default()

    if status:
        if stdout:
            data = fact.process(stdout)

    elif stderr:
        first_line = stderr[0]

        if (executor_kwargs['sudo_user'] and re.match(SUDO_REGEX, first_line)):
            status = True
        if (executor_kwargs['su_user'] and any(
            re.match(regex, first_line) for regex in SU_REGEXES
        )):
            status = True

        if not status:
            if not state.print_fact_output:
                print_host_combined_output(host, combined_output_lines)

            log_error_or_warning(host, ignore_errors, description=(
                'could not load fact: {0} {1}'
            ).format(name, get_kwargs_str(kwargs)))

    log = 'Loaded fact {0} ({1})'.format(click.style(name, bold=True), get_kwargs_str(kwargs))
    if state.print_fact_info:
        logger.info(log)
    else:
        logger.debug(log)

    # Check we've not failed
    if not status and not ignore_errors and apply_failed_hosts:
        state.fail_hosts({host})

    if fact_hash:
        host.facts[fact_hash] = data
    return data


def get_host_fact(state, host, name, args=None, kwargs=None):
    fact_hash = make_hash((name, kwargs, _get_executor_kwargs(state, host)))
    return get_fact(state, host, name, args=args, kwargs=kwargs, fact_hash=fact_hash)


def create_host_fact(state, host, name, data, args=None, kwargs=None):
    fact_hash = make_hash((name, kwargs, _get_executor_kwargs(state, host)))
    host.facts[fact_hash] = data


def delete_host_fact(state, host, name, args=None, kwargs=None):
    fact_hash = make_hash((name, kwargs, _get_executor_kwargs(state, host)))
    host.facts.pop(fact_hash, None)
