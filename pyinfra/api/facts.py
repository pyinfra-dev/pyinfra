"""
The pyinfra facts API. Facts enable pyinfra to collect remote server state which
is used to "diff" with the desired state, producing the final commands required
for a deploy.

Note that the facts API does *not* use the global currently in context host so
it's possible to call facts on hosts out of context (ie give me the IP of this
other host B while I operate on this host A).
"""

from __future__ import annotations

import inspect
import re
from inspect import getcallargs
from socket import error as socket_error, timeout as timeout_error
from typing import TYPE_CHECKING, Any, Callable, Generic, Iterable, Optional, Type, TypeVar, cast

import click
import gevent
from paramiko import SSHException
from typing_extensions import override

from pyinfra import logger
from pyinfra.api import StringCommand
from pyinfra.api.arguments import all_global_arguments, pop_global_arguments
from pyinfra.api.util import (
    get_kwargs_str,
    log_error_or_warning,
    log_host_command_error,
    print_host_combined_output,
)
from pyinfra.connectors.util import CommandOutput
from pyinfra.progress import progress_spinner

from .arguments import CONNECTOR_ARGUMENT_KEYS

if TYPE_CHECKING:
    from pyinfra.api import Host, State

SUDO_REGEX = r"^sudo: unknown user"
SU_REGEXES = (
    r"^su: user .+ does not exist",
    r"^su: unknown login",
)


T = TypeVar("T")


class FactBase(Generic[T]):
    name: str

    abstract: bool = True

    shell_executable: str | None = None

    command: Callable[..., str | StringCommand]

    def requires_command(self, *args, **kwargs) -> str | None:
        return None

    @override
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        module_name = cls.__module__.replace("pyinfra.facts.", "")
        cls.name = f"{module_name}.{cls.__name__}"

        # Check that fact's `command` method does not inadvertently take a global
        # argument, most commonly `name`.
        if hasattr(cls, "command") and callable(cls.command):
            command_args = set(inspect.signature(cls.command).parameters.keys())
            global_args = set([name for name, _ in all_global_arguments()])
            command_global_args = command_args & global_args

            if len(command_global_args) > 0:
                names = ", ".join(command_global_args)
                raise TypeError(f"{cls.name}'s arguments {names} are reserved for global arguments")

    @staticmethod
    def default() -> T:
        """
        Set the default attribute to be a type (eg list/dict).
        """

        return cast(T, None)

    def process(self, output: Iterable[str]) -> T:
        # NOTE: TypeVar does not support a default, so we have to cast this str -> T
        return cast(T, "\n".join(output))

    def process_pipeline(self, args, output):
        return {arg: self.process([output[i]]) for i, arg in enumerate(args)}


class ShortFactBase(Generic[T]):
    name: str
    fact: Type[FactBase]

    @override
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        module_name = cls.__module__.replace("pyinfra.facts.", "")
        cls.name = f"{module_name}.{cls.__name__}"

    def process_data(self, data):
        return data


def get_short_facts(state: "State", host: "Host", short_fact, **kwargs):
    fact_data = get_fact(state, host, short_fact.fact, **kwargs)
    return short_fact().process_data(fact_data)


def _make_command(command_attribute, host_args):
    if callable(command_attribute):
        host_args.pop("self", None)
        return command_attribute(**host_args)
    return command_attribute


def _handle_fact_kwargs(state: "State", host: "Host", cls, args, kwargs):
    args = args or []
    kwargs = kwargs or {}

    # Start with a (shallow) copy of current operation kwargs if any
    ctx_kwargs: dict[str, Any] = (
        cast(dict[str, Any], host.current_op_global_arguments) or {}
    ).copy()
    # Update with the input kwargs (overrides)
    ctx_kwargs.update(kwargs)

    # Pop executor kwargs, pass remaining
    global_kwargs, _ = pop_global_arguments(state, host, cast(dict[str, Any], ctx_kwargs))

    fact_kwargs = {key: value for key, value in kwargs.items() if key not in global_kwargs}

    if args or fact_kwargs:
        # Merges args & kwargs into a single kwargs dictionary
        fact_kwargs = getcallargs(cls().command, *args, **fact_kwargs)

    return fact_kwargs, global_kwargs


def get_facts(state, *args, **kwargs):
    def get_host_fact(host, *args, **kwargs):
        return get_fact(state, host, *args, **kwargs)

    greenlet_to_host = {
        state.pool.spawn(get_host_fact, host, *args, **kwargs): host
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
    state: "State",
    host: "Host",
    cls: type[FactBase],
    args: Optional[Any] = None,
    kwargs: Optional[Any] = None,
    ensure_hosts: Optional[Any] = None,
    apply_failed_hosts: bool = True,
) -> Any:
    if issubclass(cls, ShortFactBase):
        return get_short_facts(
            state,
            host,
            cls,
            args=args,
            kwargs=kwargs,
            ensure_hosts=ensure_hosts,
            apply_failed_hosts=apply_failed_hosts,
        )

    return _get_fact(
        state,
        host,
        cls,
        args,
        kwargs,
        ensure_hosts,
        apply_failed_hosts,
    )


def _get_fact(
    state: "State",
    host: "Host",
    cls: type[FactBase],
    args: Optional[list] = None,
    kwargs: Optional[dict] = None,
    ensure_hosts: Optional[Any] = None,
    apply_failed_hosts: bool = True,
) -> Any:
    fact = cls()
    name = fact.name

    fact_kwargs, global_kwargs = _handle_fact_kwargs(state, host, cls, args, kwargs)

    kwargs_str = get_kwargs_str(fact_kwargs)
    logger.debug(
        "Getting fact: %s (%s) (ensure_hosts: %r)",
        name,
        kwargs_str,
        ensure_hosts,
    )

    if not host.connected:
        host.connect(
            reason=f"to load fact: {name} ({kwargs_str})",
            raise_exceptions=True,
        )

    # Facts can override the shell (winrm powershell vs cmd support)
    if fact.shell_executable:
        global_kwargs["_shell_executable"] = fact.shell_executable

    command = _make_command(fact.command, fact_kwargs)
    requires_command = _make_command(fact.requires_command, fact_kwargs)
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
    output = CommandOutput([])

    executor_kwargs = {
        key: value for key, value in global_kwargs.items() if key in CONNECTOR_ARGUMENT_KEYS
    }

    try:
        status, output = host.run_shell_command(
            command,
            print_output=state.print_fact_output,
            print_input=state.print_fact_input,
            **executor_kwargs,
        )
    except (timeout_error, socket_error, SSHException) as e:
        log_host_command_error(
            host,
            e,
            timeout=global_kwargs.get("_timeout"),
        )

    stdout_lines, stderr_lines = output.stdout_lines, output.stderr_lines

    data = fact.default()

    if status:
        if stdout_lines:
            data = fact.process(stdout_lines)
    elif stderr_lines:
        # If we have error output and that error is sudo or su stating the user
        # does not exist, do not fail but instead return the default fact value.
        # This allows for users that don't currently but may be created during
        # other operations.
        first_line = stderr_lines[0]
        if executor_kwargs["_sudo_user"] and re.match(SUDO_REGEX, first_line):
            status = True
        if executor_kwargs["_su_user"] and any(re.match(regex, first_line) for regex in SU_REGEXES):
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
            print_host_combined_output(host, output)

        log_error_or_warning(
            host,
            global_kwargs["_ignore_errors"],
            description=("could not load fact: {0} {1}").format(name, get_kwargs_str(fact_kwargs)),
        )

    # Check we've not failed
    if apply_failed_hosts and not status and not global_kwargs["_ignore_errors"]:
        state.fail_hosts({host})

    return data
