"""Manage s6-rc services (https://www.skarnet.org/software/s6-rc/)."""

import builtins
import re
from collections.abc import Iterable

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.api.command import make_formatted_string_command
from pyinfra.facts.s6 import S6LiveStatus, S6SetStatus
from pyinfra.facts.files import FindInFile
from pyinfra.operations import files


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
    # TODO implement this
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

    # `service` is treated as an iterable of strings; if it is a string itself (i.e. one service
    # specified), undesired iteration over characters will occur.
    if isinstance(service, str):
        service = (service,)

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

    # TODO call s6.set operation, don't implement set-based logic here

    # offline set management
    if enabled is not None:
        set_statuses = {srv: host.get_fact(S6SetStatus, set).data[srv] for srv in service}
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


# for now, no support for custom repository; only the s6-frontend one.
# but should get this at some point, as it allows for user-managed (i.e. non-root) services
# TODO multiple sets at once
@operation(
    is_idempotent=False,
    idempotent_notice="If `commit=True`, the operation is stateless due to an unconditional `s6 set check -F` and `s6 set commit`. Otherwise it is idempotent.",
)
def set(
    set: str,
    prescriptions: dict[str] | None = None,
    enforce_prescriptions: bool = False,
    present: bool = True,
    save: bool = False,
    save_name: str = set,
    force_save: bool = False,
    backup: bool = True,
    commit: bool = True,
    # TODO configurable s6-frontend.conf location
):
    """
    Manage sets in a repository.

    + set: name of the set to manage.
    + prescriptions: the prescriptions to ensure in the set. A map of service name -> prescription, where the prescription is any of "always", "active", "usable", "masked". May be `None`, which allows management of set presence only.
    + enforce_prescriptions: whether the `prescriptions` should be the *only* prescriptions in the set (i.e. other services will be removed)
    + present: whether the set should be present in the repository.
    + save: whether to save the set to the repository.
    + save_name: name for the saved set.
    + force_save: whether to overwrite existing sets.
    + backup: whether to backup overwritten sets by appending the timestamp to the directory name.
    + commit: whether to commit the current(ly loaded) set. Delaying this step can allow for other operations to modify the current set, with the final result being committed at the end.

    """

    if set == "current":
        raise ValueError('set name cannot be "current"')

    if prescriptions:
        if not (builtins.set(prescriptions.values()) <= {"always", "active", "usable", "masked"}):
            raise ValueError(
                'prescriptions can only take values "always", "active", "usable", or "masked"'
            )

        wanted_always = [srv for srv, rx in prescriptions.items() if rx == "always"]
        wanted_active = [srv for srv, rx in prescriptions.items() if rx == "active"]
        wanted_usable = [srv for srv, rx in prescriptions.items() if rx == "usable"]
        wanted_masked = [srv for srv, rx in prescriptions.items() if rx == "masked"]

    if present:
        # prescription of every service in the set
        curr_rxs = host.get_fact(S6SetStatus, set)
        if enforce_prescriptions:
            # mask all services not present in `prescriptions` arg
            wanted_masked.extend([srv for srv in curr_rxs if srv not in prescriptions])
        # TODO there has to be a way to reduce boilerplate
        if prescriptions and prescriptions != curr_rxs:
            yield make_formatted_string_command("s6 set load {0}", QuoteString(set))

            if wanted_always:
                service_subset = []
                for srv in wanted_always:
                    try:
                        if curr_rxs[srv] != "always":
                            service_subset.append(srv)
                    except KeyError:
                        service_subset.append(srv)
                if service_subset:
                    yield from _make_set_rx_command("make-essential", service_subset)
            if wanted_active:
                service_subset = []
                for srv in wanted_active:
                    try:
                        if curr_rxs[srv] != "active":
                            service_subset.append(srv)
                    except KeyError:
                        service_subset.append(srv)
                if service_subset:
                    yield from _make_set_rx_command("enable", service_subset)
            if wanted_usable:
                service_subset = []
                for srv in wanted_usable:
                    try:
                        if curr_rxs[srv] != "usable":
                            service_subset.append(srv)
                    except KeyError:
                        service_subset.append(srv)
                if service_subset:
                    yield from _make_set_rx_command("disable", service_subset)
            if wanted_masked:
                service_subset = []
                for srv in wanted_masked:
                    try:
                        if curr_rxs[srv] != "masked":
                            service_subset.append(srv)
                    except KeyError:
                        service_subset.append(srv)
                if service_subset:
                    yield from _make_set_rx_command("mask", service_subset)

            if save:
                if save_name:
                    yield make_formatted_string_command("s6 set save {0}", QuoteString(save_name))
                else:
                    yield StringCommand("s6 set save")


        elif prescriptions and not commit:
            host.noop("all services specified match the desired prescriptions and commit not requested")

        if force_save:
            if backup:
                # will break if repodir key pair in /etc/s6-frontend.conf spans several lines
                lines = host.get_fact(
                    FindInFile,
                    "/etc/s6-frontend.conf",
                    r"repodir\s*=",
                    interpolate_variables=False,
                    extended_regex=True,
                ).data
                if lines is None:
                    raise RuntimeError(
                        "no repodir found in /etc/s6-frontend.conf, or file doesn't exist"
                    )
                if len(lines) != 1:
                    raise RuntimeWarning(
                        "multiple repodir definitions found in /etc/s6-frontend.conf, using the first one"
                    )

                # https://skarnet.org/software/execline/envfile.html#syntax
                repodir = re.fullmatch(r'^\s*repodir\s*=\s*(/[^\s]*|"/.*")\s*$', lines[0])[1]

                yield from files.directory._inner(
                    path=repodir, present=False, force=True, force_backup=True
                )

            yield make_formatted_string_command("s6 set save -f {0}", QuoteString(set))

        # TODO mark stateless
        if commit:
            yield StringCommand("s6 set check -F")
            yield StringCommand("s6 set commit")

    # present=False
    else:
        yield make_formatted_string_command("s6 set delete {0}", QuoteString(set))


# TODO s6 set commit op
# TODO s6 live install is analagous to systemd daemon-reload
