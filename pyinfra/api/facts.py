"""
The pyinfra facts API. Facts enable pyinfra to collect remote server state which
is used to "diff" with the desired state, producing the final commands required
for a deploy.
"""

import re
from inspect import getcallargs
from socket import error as socket_error, timeout as timeout_error

import click
import gevent
from paramiko import SSHException

from pyinfra import logger
from pyinfra.api import StringCommand
from pyinfra.api.arguments import pop_global_arguments
from pyinfra.api.util import (
    get_kwargs_str,
    log_error_or_warning,
    log_host_command_error,
    make_hash,
    print_host_combined_output,
)
from pyinfra.connectors.util import split_combined_output
from pyinfra.progress import progress_spinner

from .arguments import get_executor_kwarg_keys

SUDO_REGEX = r"^sudo: unknown user:"
SU_REGEXES = (
    r"^su: user .+ does not exist",
    r"^su: unknown login",
)


class FactNameMeta(type):
    def __init__(cls, name, bases, attrs):
        module_name = cls.__module__.replace("pyinfra.facts.", "")
        cls.name = f"{module_name}.{cls.__name__}"


class FactBase(object, metaclass=FactNameMeta):
    abstract = True

    shell_executable = None

    requires_command = None

    @staticmethod
    def default():
        """
        Set the default attribute to be a type (eg list/dict).
        """

    @staticmethod
    def process(output):
        return "\n".join(output)

    def process_pipeline(self, args, output):
        return {arg: self.process([output[i]]) for i, arg in enumerate(args)}


class ShortFactBase(object, metaclass=FactNameMeta):
    fact = None


def get_short_facts(state, host, short_fact, **kwargs):
    fact_data = get_fact(state, host, short_fact.fact, **kwargs)
    return short_fact.process_data(fact_data)


def _make_command(command_attribute, host_args):
    if callable(command_attribute):
        host_args.pop("self", None)
        return command_attribute(**host_args)
    return command_attribute


def _get_executor_kwargs(state, host, override_kwargs=None, override_kwarg_keys=None):
    if override_kwargs is None:
        override_kwargs = {}
        override_kwarg_keys = []

    # Apply any current op kwargs that *weren't* found in the overrides
    override_kwargs.update(
        {
            key: value
            for key, value in (host.current_op_global_kwargs or {}).items()
            if key not in override_kwarg_keys
        },
    )

    return {
        key: value for key, value in override_kwargs.items() if key in get_executor_kwarg_keys()
    }


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
    cls,
    args=None,
    kwargs=None,
    ensure_hosts=None,
    apply_failed_hosts=True,
    fact_hash=None,
    use_cache=True,
):
    if issubclass(cls, ShortFactBase):
        return get_short_facts(state, host, cls, args=args, ensure_hosts=ensure_hosts)

    with host.facts_lock:
        if use_cache and fact_hash and fact_hash in host.facts:
            return host.facts[fact_hash]

        return _get_fact(
            state,
            host,
            cls,
            args,
            kwargs,
            ensure_hosts,
            apply_failed_hosts,
            fact_hash,
        )


def _get_fact(
    state,
    host,
    cls,
    args=None,
    kwargs=None,
    ensure_hosts=None,
    apply_failed_hosts=True,
    fact_hash=None,
):
    fact = cls()
    name = fact.name

    args = args or ()
    kwargs = kwargs or {}

    # Get the defaults *and* overrides by popping from kwargs, executor kwargs passed
    # into get_fact override everything else (applied below).
    override_kwargs, override_kwarg_keys = pop_global_arguments(
        kwargs,
        state=state,
        host=host,
        keys_to_check=get_executor_kwarg_keys(),
    )

    executor_kwargs = _get_executor_kwargs(
        state,
        host,
        override_kwargs=override_kwargs,
        override_kwarg_keys=override_kwarg_keys,
    )

    if args or kwargs:
        # Merges args & kwargs into a single kwargs dictionary
        kwargs = getcallargs(fact.command, *args, **kwargs)

    kwargs_str = get_kwargs_str(kwargs)
    logger.debug(
        "Getting fact: {0} ({1}) (ensure_hosts: {2})".format(
            name,
            kwargs_str,
            ensure_hosts,
        ),
    )

    if not host.connected:
        host.connect(
            reason=f"to load fact: {name} ({kwargs_str})",
            raise_exceptions=True,
        )

    ignore_errors = (host.current_op_global_kwargs or {}).get(
        "ignore_errors",
        state.config.IGNORE_ERRORS,
    )

    # Facts can override the shell (winrm powershell vs cmd support)
    if fact.shell_executable:
        executor_kwargs["shell_executable"] = fact.shell_executable

    command = _make_command(fact.command, kwargs)
    requires_command = _make_command(fact.requires_command, kwargs)
    if requires_command:
        command = StringCommand(
            # Command doesn't exist, return 0 *or* run & return fact command
            "!",
            "command",
            "-v",
            requires_command,
            ">/dev/null",
            "||",
            command,
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
            host,
            e,
            timeout=executor_kwargs["timeout"],
        )

    stdout, stderr = split_combined_output(combined_output_lines)

    data = fact.default()

    if status:
        if stdout:
            data = fact.process(stdout)
    elif stderr:
        # If we have error output and that error is sudo or su stating the user
        # does not exist, do not fail but instead return the default fact value.
        # This allows for users that don't currently but may be created during
        # other operations.
        first_line = stderr[0]
        if executor_kwargs["sudo_user"] and re.match(SUDO_REGEX, first_line):
            status = True
        if executor_kwargs["su_user"] and any(re.match(regex, first_line) for regex in SU_REGEXES):
            status = True

    if status:
        log_message = "{0}{1}".format(
            host.print_prefix,
            "Loaded fact {0}{1}".format(
                click.style(name, bold=True),
                f" ({get_kwargs_str(kwargs)})" if kwargs else "",
            ),
        )
        if state.print_fact_info:
            logger.info(log_message)
        else:
            logger.debug(log_message)
    else:
        if not state.print_fact_output:
            print_host_combined_output(host, combined_output_lines)

        log_error_or_warning(
            host,
            ignore_errors,
            description=("could not load fact: {0} {1}").format(name, get_kwargs_str(kwargs)),
        )

    # Check we've not failed
    if not status and not ignore_errors and apply_failed_hosts:
        state.fail_hosts({host})

    if fact_hash:
        host.facts[fact_hash] = data
    return data


def _get_fact_hash(state, host, cls, args, kwargs):
    args = args or None
    kwargs = kwargs or None
    return make_hash((cls, args, kwargs, _get_executor_kwargs(state, host)))


def get_host_fact(state, host, cls, args=None, kwargs=None):
    fact_hash = _get_fact_hash(state, host, cls, args, kwargs)
    return get_fact(state, host, cls, args=args, kwargs=kwargs, fact_hash=fact_hash)


def reload_host_fact(state, host, cls, args=None, kwargs=None):
    fact_hash = _get_fact_hash(state, host, cls, args, kwargs)
    return get_fact(
        state,
        host,
        cls,
        args=args,
        kwargs=kwargs,
        fact_hash=fact_hash,
        use_cache=False,
    )


def create_host_fact(state, host, cls, data, args=None, kwargs=None):
    fact_hash = _get_fact_hash(state, host, cls, args, kwargs)
    host.facts[fact_hash] = data


def delete_host_fact(state, host, cls, args=None, kwargs=None):
    fact_hash = _get_fact_hash(state, host, cls, args, kwargs)
    host.facts.pop(fact_hash, None)
