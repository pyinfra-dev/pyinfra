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

_rx_to_subcommand = {
    "always": "make-essential",
    "active": "enable",
    "usable": "disable",
    "masked": "mask",
}


def _make_live_command(op: str, services: Iterable):
    """
    + op: the operation, e.g. "start", "stop", "restart".
    + services: the service(s) to operate on.
    """

    s = " ".join([f"{{{i}}}" for i in range(len(services))])
    yield make_formatted_string_command(f"s6 live {op} " + s, *map(QuoteString, services))


def _make_set_command(services: list, curr_rxs: dict, wanted_rx: str):
    """
    + services: the services to be assigned a specific prescription.
    + curr_rxs: the current prescriptions for all services (from the S6SetStatus fact).
    + wanted_rx: the prescription to assign to each service.
    """
    # services that need their prescription changed (not all of them; those that are already in the
    # desired state are not in this list)
    service_subset = []

    for srv in services:
        try:
            if curr_rxs[srv] != wanted_rx:
                service_subset.append(srv)
        except KeyError:
            service_subset.append(srv)

    if service_subset:
        op = _rx_to_subcommand[wanted_rx]
        s = " ".join([f"{{{i}}}" for i in range(len(service_subset))])
        yield make_formatted_string_command(f"s6 set {op} " + s, *map(QuoteString, service_subset))


# for now, no support for custom repository; only the s6-frontend one.
# but should get this at some point, as it allows for user-managed (i.e. non-root) services
@operation(
    is_idempotent=False,
    idempotent_notice="If `commit=True`, the operation is stateless due to an unconditional `s6 set check -F` and `s6 set commit`. Otherwise it is idempotent.",
)
def set(
    the_set: str = "current",
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
        curr_rxs = host.get_fact(S6SetStatus, the_set)
        if enforce_prescriptions:
            # mask all services not present in `prescriptions` arg
            wanted_masked.extend([srv for srv in curr_rxs if srv not in prescriptions])

        # TODO there has to be a way to reduce boilerplate
        if prescriptions and prescriptions != curr_rxs:
            if the_set != "current":
                yield make_formatted_string_command("s6 set load {0}", QuoteString(the_set))

            if wanted_always:
                yield from _make_set_command(wanted_always, curr_rxs, "always")
                # yield from _s6_set_helper(wanted_always, curr_rxs, "always")
                # service_subset = []
                # for srv in wanted_always:
                #    try:
                #        if curr_rxs[srv] != "always":
                #            service_subset.append(srv)
                #    except KeyError:
                #        service_subset.append(srv)
                # if service_subset:
                #    yield from _make_set_rx_command("make-essential", service_subset)
            if wanted_active:
                yield from _make_set_command(wanted_active, curr_rxs, "active")
                # yield from _s6_set_helper(wanted_active, curr_rxs, "active")
                # service_subset = []
                # for srv in wanted_active:
                #    try:
                #        if curr_rxs[srv] != "active":
                #            service_subset.append(srv)
                #    except KeyError:
                #        service_subset.append(srv)
                # if service_subset:
                #    yield from _make_set_rx_command("enable", service_subset)
            if wanted_usable:
                yield from _make_set_command(wanted_usable, curr_rxs, "usable")
                # yield from _s6_set_helper(wanted_usable, curr_rxs, "usable")
                # service_subset = []
                # for srv in wanted_usable:
                #    try:
                #        if curr_rxs[srv] != "usable":
                #            service_subset.append(srv)
                #    except KeyError:
                #        service_subset.append(srv)
                # if service_subset:
                #    yield from _make_set_rx_command("disable", service_subset)
            if wanted_masked:
                yield from _make_set_command(wanted_masked, curr_rxs, "masked")
                # yield from _s6_set_helper(wanted_masked, curr_rxs, "masked")
                # service_subset = []
                # for srv in wanted_masked:
                #    try:
                #        if curr_rxs[srv] != "masked":
                #            service_subset.append(srv)
                #    except KeyError:
                #        service_subset.append(srv)
                # if service_subset:
                #    yield from _make_set_rx_command("mask", service_subset)

            if save:
                if save_name:
                    yield make_formatted_string_command("s6 set save {0}", QuoteString(save_name))
                else:
                    yield StringCommand("s6 set save")

        elif prescriptions and not commit:
            host.noop(
                "all services specified match the desired prescriptions and commit not requested"
            )

        if force_save:
            if backup:
                # will break if repodir key pair in /etc/s6-frontend.conf spans several lines
                lines = host.get_fact(
                    FindInFile,
                    "/etc/s6-frontend.conf",
                    r"repodir\s*=",
                    interpolate_variables=False,
                    extended_regex=True,
                )
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

            yield make_formatted_string_command("s6 set save -f {0}", QuoteString(the_set))

        # TODO make this not do anything if not needed? how? separate operation?
        if commit:
            yield StringCommand("s6 set check -F")
            yield StringCommand("s6 set commit")

    # present=False
    else:
        yield make_formatted_string_command("s6 set delete {0}", QuoteString(the_set))


# TODO server.service compatibility (must use a string for services in that implementation)
@operation()
def service(
    service: str | Iterable[str],
    running: bool | None = None,
    restarted: bool | None = None,
    reloaded: bool | None = None,
    # TODO command
    command: str | None = None,
    enabled: bool | None = None,
    reload_signal: str = "SIGHUP",
    the_set: str = "current",
    enabled_rx: str = "active",
    disabled_rx: str = "usable",
    commit_set: bool = False,
    install_set: bool = False,
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
    + the_set: name of the set to use when managing enabled status, using the set named "current" by default.
    + enabled_rx: name of the prescription to assign to the service(s) when enabled, which could be either "active" or "always"
    + disabled_rx: name of the prescription to assign to the service(s) when disabled, which could be either "usable" or "masked"
    + commit_set: whether to commit the current(ly loaded) set. Delaying this step can allow for other operations to modify the current set, with the final result being committed at the end.
    + install_set: whether to install the compiled service database (the result of a commit operation) into the live state. This is analagous to systemd's daemon-reload, but not completely: systemd recognizes changes to service files after a reboot, but s6 does not. It only recognizes changes when an s6 live install command is executed. Live state replacement and enablement/disablement of services are coupled in s6.

    Specifying multiple services is preferred: fewer commands will be executed, especially in the
    case of changing the enabled status of the service, where the service database is recompiled per
    command. Note that this operation does not give as granular control over prescriptions as the
    set operation does; all services will be assigned the same prescription.
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
    if (running, restarted, reloaded) != (None,) * 3:
        # dict[str, bool] whether the services given in the services arg are running.
        live_statuses = {srv: host.get_fact(S6LiveStatus)[srv] for srv in service}
        all_up = all(live_statuses.values())
        some_up = any(live_statuses.values())
        all_down_services = [srv for srv, stat in live_statuses.items() if not stat]
        all_up_services = [srv for srv, stat in live_statuses.items() if stat]

        if running is False:
            if some_up:
                yield from _make_live_command("stop", all_up_services)
            else:
                host.noop(f"all specified services are already down: {service}")

        if running is True:
            if not all_up:
                yield from _make_live_command("start", all_down_services)
            else:
                host.noop(f"all specified services are already up: {service}")

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

    # TODO: test masked services present in `services` arg on a real system
    # offline set management
    if enabled is not None:
        if enabled is True:
            yield from set._inner(the_set=the_set, prescriptions={srv: enabled_rx for srv in service})

        if enabled is False:
            yield from set._inner(the_set=the_set, prescriptions={srv: disabled_rx for srv in service})

        # s6.set operation already handles s6 set load
        # TODO look at how systemd daemon-reload handles this, or maybe a daemon-reload like
        # operation not necessary
        if commit_set:
            yield StringCommand("s6 set check -F")
            yield StringCommand("s6 set commit")
            if install_set:
                yield StringCommand("s6 live install")

        # TODO
        if command:
            yield StringCommand(command)
