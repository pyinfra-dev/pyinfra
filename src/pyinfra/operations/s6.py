"""Manage s6-rc services (https://www.skarnet.org/software/s6-rc/)."""

from collections.abc import Iterable

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.api.command import make_formatted_string_command
from pyinfra.facts.s6 import S6LiveStatus, S6SetStatus


def _make_live_command(op: str, services: Iterable):
    """
    + op: the operation, e.g. "start", "stop", "restart".
    + services: the service(s) to operate on.
    """

    s = " ".join([f"{{{i}}}" for i in range(len(services))])
    yield make_formatted_string_command(f"s6 live {op} " + s, *map(QuoteString, services))


def _make_set_rx_command(op: str, services: Iterable):
    """
    + rx: the operation, one of "enable", "disable", "mask", "unmask", "make-essential".
    + services: the service(s) to operate on.
    """
    s = " ".join([f"{{{i}}}" for i in range(len(services))])
    yield make_formatted_string_command(f"s6 set {op} " + s, *map(QuoteString, services))


# TODO server.service compatibility (must use a string for services in that implementation)
@operation()
def service(
    service: str | Iterable[str],
    # optional, to separate live management vs set management
    running: bool | None = True,
    restarted: bool = False,
    reloaded: bool = False,
    # TODO command
    command: str | None = None,
    enabled: bool | None = None,
    reload_signal: str = "SIGHUP",
    # TODO repo
    repo: str | None = None,
    # TODO set
    set: str | None = None,
    enabled_rx: str = "active",
    disabled_rx: str = "usable",
):
    """
    Manage the state of s6-supervised services.

    + services: name(s) of the service(s) to manage.
    + running: whether the service(s) should be under an s6-supervise.
    + restarted: whether the service(s) should be restarted
    + reloaded: whether the service(s) should be reloaded by sending a SIGHUP. Whether the service is reloaded depends on how it handles SIGHUP.
    + command: custom command to run after the auto-computed commands.
    + enabled: whether the service should be given an "active" or "usable" prescription
    + reload_signal: the signal to send to the service(s) when a reload is desired.
    + repo: name of the repository to use when managing enabled status, using the one configured in s6-frontend.conf by default.
    + set: name of the set to use when managing enabled status, using the set named "current" by default.
    + enabled_rx: name of the prescription to assign to the service(s) when enabled, which could be either "active" or "always"
    + disabled_rx: name of the prescription to assign to the service(s) when disabled, which could be either "usable" or "masked"

    Specifying multiple services is preferred: fewer commands will be executed, especially in the case of changing the enabled status of the service, where the service database is recompiled per command.
    """

    if enabled_rx not in {"active", "always"}:
        raise ValueError('enabled_rx must be either "active" or "always"')
    if disabled_rx not in {"usable", "masked"}:
        raise ValueError('disabled_rx must be either "usable" or "masked"')

    # because iterable unpacking is used
    if isinstance(service, str):
        service = (service,)

    # Tuple[bool] of status of each service in services arg
    # specified_status = (
    #    itemgetter(*services)(all_status) if len(all_status) != 1 else (all_status[services[0]]),
    # )
    # dict[str, bool] of status of each service in services arg
    # all_running = True if all(itemgetter(*services)(all_status)) else False

    # live state management
    if running is not None:

        # dict[str, bool] whether the services given in the services arg are running.
        live_statuses = {srv: host.get_fact(S6LiveStatus).data[srv] for srv in service}
        all_up = all(live_statuses.values())
        some_up = any(live_statuses.values())
        all_down_services = [srv for srv, stat in live_statuses.items() if not stat]
        all_up_services = [srv for srv, stat in live_statuses.items() if stat]

        if running:
            if not all_up:
                yield from _make_live_command("start", all_down_services)
            else:
                host.noop(f"all specified services are already up: {service}")

        else:
            if some_up:
                yield from _make_live_command("stop", all_up_services)
            else:
                host.noop(f"all specified services are already down: {service}")

        if restarted:
            if some_up:
                yield from _make_live_command("restart", all_up_services)
            else:
                host.noop(f"all specified services are down: {service}")

        if reloaded:
            if some_up:
                yield make_formatted_string_command(
                    "s6 process kill -s {0} "
                    + " ".join([f"{{{i + 1}}}" for i in range(len(all_up_services))]),
                    QuoteString(reload_signal),
                    *map(QuoteString, all_up_services),
                )
            else:
                host.noop(f"all specified services are down: {service}")

    # TODO: if a service is masked, s6 live will always fail to do anything to that service;
    # potential solution is to split enabled into another operation
    # ERROR CONDITION: a masked service is present in `services` arg.

    # offline set management
    if enabled is not None:

        set_statuses = {srv: host.get_fact(S6SetStatus).data[srv] for srv in service}
        all_enabled_services = [
            srv for srv, stat in set_statuses.items() if stat in {"active", "always"}
        ]
        all_disabled_services = [
            srv for srv, stat in set_statuses.items() if stat in {"usable", "masked"}
        ]

        if enabled:
            if len(all_disabled_services) != 0:
                yield from _make_set_rx_command("enable", all_disabled_services)
                yield StringCommand("s6 set check -F")
                yield StringCommand("s6 set commit")
            else:
                host.noop(f"all services are already enabled: {service}")

        else:
            if len(all_enabled_services) != 0:
                yield from _make_set_rx_command("disable", all_enabled_services)
                yield StringCommand("s6 set check -F")
                yield StringCommand("s6 set commit")
            else:
                host.noop(f"all services are already disabled: {service}")

        if command:
            yield StringCommand(command)


# TODO s6 live install is analagous to systemd daemon-reload
# for now, no support for custom repository; only the s6-frontend one.
# but should get this at some point, as it allows for user-managed (i.e. non-root) services
@operation()
def set(
    set: str = "current",
    present: bool = True,
    force_save: bool = False,
    backup: bool = True,
):
    """
    Manage sets in a repository.

    + set: name of the set to manage.
    + present: whether the set should be present in the repository.
    + force_save: whether to overwrite existing sets.
    + backup: whether to backup overwritten sets by appending the date to the directory name.
    """

    if not present:
        yield make_formatted_string_command("s6 set delete {0}", QuoteString(set))

    if force_save:
        yield make_formatted_string_command("s6 set save -f {0}", QuoteString(set))
    else:
        yield make_formatted_string_command("s6 set save {0}", QuoteString(set))

    "s6-rc-set-new"
    "s6-rc-set-copy"
    "s6-rc-set-delete"
    # run after each update to check consistency, but don't autofix
    "s6-rc-set-fix"


# TODO operation for set commit?
