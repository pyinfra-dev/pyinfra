"""
The pyinfra facts API. Facts enable pyinfra to collect remote server state which
is used to "diff" with the desired state, producing the final commands required
for a deploy.

Note that the facts API does *not* use the global currently in context host so
it's possible to call facts on hosts out of context (ie give me the IP of this
other host B while I operate on this host A).
"""

from __future__ import annotations

import re
from inspect import getcallargs
from socket import error as socket_error, timeout as timeout_error
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterable,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

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
from pyinfra.connectors.util import CommandOutput
from pyinfra.context import ctx_host, ctx_state
from pyinfra.progress import progress_spinner

from .arguments import CONNECTOR_ARGUMENT_KEYS

if TYPE_CHECKING:
    from pyinfra.api.host import Host
    from pyinfra.api.state import State

SUDO_REGEX = r"^sudo: unknown user"
SU_REGEXES = (
    r"^su: user .+ does not exist",
    r"^su: unknown login",
)


T = TypeVar("T")


class FactBase(Generic[T]):
    name: str

    abstract: bool = True

    shell_executable: Optional[str] = None

    requires_command: Optional[str] = None

    command: Union[str, Callable]

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        module_name = cls.__module__.replace("pyinfra.facts.", "")
        cls.name = f"{module_name}.{cls.__name__}"

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

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        module_name = cls.__module__.replace("pyinfra.facts.", "")
        cls.name = f"{module_name}.{cls.__name__}"

    @staticmethod
    def process_data(data):
        return data


def get_short_facts(state: "State", host: "Host", short_fact, **kwargs):
    fact_data = get_fact(state, host, short_fact.fact, **kwargs)
    return short_fact().process_data(fact_data)


def _make_command(command_attribute, host_args):
    if callable(command_attribute):
        host_args.pop("self", None)
        return command_attribute(**host_args)
    return command_attribute


def _get_executor_kwargs(
    state: "State",
    host: "Host",
    override_kwargs: Optional[dict[str, Any]] = None,
    override_kwarg_keys: Optional[list[str]] = None,
):
    if override_kwargs is None:
        override_kwargs = {}
    if override_kwarg_keys is None:
        override_kwarg_keys = []

    # Use the current operation global kwargs, or generate defaults
    global_kwargs = host.current_op_global_arguments
    if not global_kwargs:
        global_kwargs, _ = pop_global_arguments({}, state, host)

    # Apply any current op kwargs that *weren't* found in the overrides
    override_kwargs.update(
        {key: value for key, value in global_kwargs.items() if key not in override_kwarg_keys},
    )

    return {key: value for key, value in override_kwargs.items() if key in CONNECTOR_ARGUMENT_KEYS}


def _handle_fact_kwargs(state, host, cls, args, kwargs):
    args = args or []
    kwargs = kwargs or {}

    # TODO: this is here to avoid popping stuff accidentally, this is horrible! Change the
    # pop function to return the clean kwargs to avoid the indirect mutation.
    kwargs = kwargs.copy()

    # Get the defaults *and* overrides by popping from kwargs, executor kwargs passed
    # into get_fact override everything else (applied below).
    override_kwargs, override_kwarg_keys = pop_global_arguments(
        kwargs,
        state=state,
        host=host,
        keys_to_check=CONNECTOR_ARGUMENT_KEYS,
    )

    executor_kwargs = _get_executor_kwargs(
        state,
        host,
        override_kwargs=override_kwargs,  # type: ignore[arg-type]
        override_kwarg_keys=override_kwarg_keys,
    )

    fact_kwargs = {}

    if args or kwargs:
        assert not isinstance(cls.command, str)
        # Merges args & kwargs into a single kwargs dictionary
        fact_kwargs = getcallargs(cls().command, *args, **kwargs)

    return fact_kwargs, executor_kwargs


def get_facts(state: "State", *args, **kwargs):
    def get_fact_with_context(state, host, *args, **kwargs):
        with ctx_state.use(state):
            with ctx_host.use(host):
                return get_fact(state, host, *args, **kwargs)

    greenlet_to_host = {
        state.pool.spawn(get_fact_with_context, state, host, *args, **kwargs): host
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

    fact_kwargs, executor_kwargs = _handle_fact_kwargs(state, host, cls, args, kwargs)

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

    ignore_errors = (
        host.current_op_global_arguments["_ignore_errors"]
        if host.in_op and host.current_op_global_arguments
        else state.config.IGNORE_ERRORS
    )

    # Facts can override the shell (winrm powershell vs cmd support)
    if fact.shell_executable:
        executor_kwargs["_shell_executable"] = fact.shell_executable

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
            timeout=executor_kwargs["_timeout"],
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
            ignore_errors,
            description=("could not load fact: {0} {1}").format(name, get_kwargs_str(fact_kwargs)),
        )

    # Check we've not failed
    if not status and not ignore_errors and apply_failed_hosts:
        state.fail_hosts({host})

    return data


def _get_fact_hash(state: "State", host: "Host", cls, args, kwargs):
    if issubclass(cls, ShortFactBase):
        cls = cls.fact
    fact_kwargs, executor_kwargs = _handle_fact_kwargs(state, host, cls, args, kwargs)
    return make_hash((cls, fact_kwargs, executor_kwargs))


def get_host_fact(
    state: "State",
    host: "Host",
    cls,
    args: Optional[Iterable] = None,
    kwargs: Optional[dict] = None,
) -> Any:
    return get_fact(state, host, cls, args=args, kwargs=kwargs)
