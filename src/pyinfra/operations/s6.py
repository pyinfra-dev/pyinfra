"""Manage s6-rc services (https://www.skarnet.org/software/s6-rc/)."""

from operator import itemgetter
from collections.abc import Iterable
from itertools import chain

from pyinfra import host
from pyinfra.api import QuoteString, operation
from pyinfra.api.command import make_formatted_string_command
from pyinfra.facts.s6 import S6LiveStatus


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


# TODO server.service compatibility (must use a string for services in that implementation)
@operation()
def service(
    services: str | Iterable[str],
    running: bool = True,
    restarted: bool = False,
    reloaded: bool = False,
    command: str | None = None,
    enabled: bool | None = None,
    reload_signal: str = "SIGHUP",
    repo: str | None = None,
    set: str | None = None,
    enabled_rx: str = "active",
    disabled_rx: str = "usable",
):
    """
    Manage the state of s6-supervised services.

    + services: name(s) of the service(s) to manage.
    + running: whether the service(s) should be under an s6-supervise.
    + restarted: whether the service(s) should be restarted (with `s6-rc -d change service && s6-rc -u change service`)
    + reloaded: whether the service(s) should be reloaded by sending a SIGHUP. Whether the service is reloaded depends on how it handles SIGHUP.
    + command: TODO
    + enabled: whether the service should be given an "active" or "usable" prescription
    + reload_signal: the signal to send to the service(s) when a reload is desired.
    + repo: name of the repository to use when managing enabled status, using the one configured in s6-frontend.conf by default.
    + set: name of the set to use when managing enabled status, using the set named "current" by default.
    + enabled_rx: name of the prescription to assign to the service(s) when enabled, which could be either "active" or "always"
    + disabled_rx: name of the prescription to assign to the service(s) when disabled, which could be either "usable" or "masked"

    If multiple services are specified, s6 will automatically handle dependency management.
    """

    if enabled_rx not in {"active", "always"}:
        raise ValueError('enabled_rx must be either "active" or "always"')
    if disabled_rx not in {"usable", "masked"}:
        raise ValueError('disabled_rx must be either "usable" or "masked"')

    # because iterable unpacking is used
    if isinstance(services, str):
        services = (services,)

    # Tuple[bool] of status of each service in services arg
    # specified_status = (
    #    itemgetter(*services)(all_status) if len(all_status) != 1 else (all_status[services[0]]),
    # )
    # dict[str, bool] of status of each service in services arg
    # all_running = True if all(itemgetter(*services)(all_status)) else False

    # dict[str, bool] whether the services given in the services arg are running.
    statuses = {srv: host.get_fact(S6LiveStatus).data[srv] for srv in services}
    all_up = all(statuses.values())
    some_up = any(statuses.values())

    services_concat_string = QuoteString(" ".join(services))
    running_services_concat_string = QuoteString(
        " ".join([srv for srv, status in statuses.items() if status])
    )

    # ===
    # idempotency logic
    # ===

    all_down_services = [srv for srv, stat in statuses.items() if not stat]
    all_up_services = [srv for srv, stat in statuses.items() if stat]

    # requested to bring up given services
    # bring up all specified services that are down
    if running:
        if not all_up:
            yield make_formatted_string_command(
                # e.g. "s6 live start {0} {1} {2} {3}" if there are 4 down services
                "s6 live start " + " ".join([f"{{{i}}}" for i in range(len(all_down_services))]),
                *map(QuoteString, all_down_services),
            )
        else:
            host.noop(f"all specified services are already up: {services}")

    # requested to bring down given services
    # bring down all specified services that are up
    else:
        if some_up:
            yield make_formatted_string_command(
                "s6 live stop " + " ".join([f"{{{i}}}" for i in range(len(all_up_services))]),
                *map(QuoteString, all_up_services),
            )
        else:
            host.noop(f"all specified services are already down: {services}")

    # only restart services that are up
    if restarted:
        if some_up:
            yield make_formatted_string_command(
                "s6 live restart " + " ".join([f"{{{i}}}" for i in range(len(all_up_services))]),
                *map(QuoteString, all_up_services),
            )
        else:
            host.noop(f"all specified services are down: {services}")

    # only reload services that are up
    if reloaded:
        if some_up:
            yield make_formatted_string_command(
                "s6 process kill -s {0} "
                + " ".join([f"{{{i+1}}}" for i in range(len(all_up_services))]),
                QuoteString(reload_signal),
                *map(QuoteString, all_up_services),
            )
        else:
            host.noop(f"all specified services are down: {services}")

    # if not running:
    #    if all_up:
    #        yield make_formatted_string_command("s6 live stop {0}", services_concat_string)
    #    elif len(services) == 1:
    #        host.noop(f"service {' '.join(services)} is stopped")
    #    else:
    #        host.noop(f"services {' '.join(services)} are stopped")

    # if running:
    #    if not all_up:
    #        yield make_formatted_string_command("s6 live start {0}", services_concat_string)
    #    elif len(services) == 1:
    #        host.noop(f"service {' '.join(services)} is running")
    #    else:
    #        host.noop(f"service {' '.join(services)} are running")

    # if restarted and some_up:
    #    # restarts only the running services
    #    yield make_formatted_string_command("s6 live restart {0}", running_services_concat_string)

    # if reloaded and all_up:
    #    yield make_formatted_string_command(
    #        "s6 process kill -s {0} {1}", reload_signal, services_concat_string
    #    )

    # ===
    # enable/disable services
    # ===

    # TODO case "unmasked"
    enabled_subcommand = "make-essential" if enabled_rx == "always" else "enable"
    disabled_subcommand = "mask" if disabled_rx == "masked" else "disable"

    if enabled:
        if repo and set:
            yield make_formatted_string_command(
                "s6-rc-set-change -r {0} {1} {2} {3}",
                QuoteString(repo),
                QuoteString(set),
                QuoteString(enabled_rx),
                services_concat_string,
            )
        elif not repo and set:
            yield make_formatted_string_command(
                "s6-rc-set-change {0} {1} {2}",
                QuoteString(set),
                QuoteString(enabled_rx),
                services_concat_string,
            )
        elif repo and not set:
            yield make_formatted_string_command(
                "s6-rc-set-change -r {0} current {1} {2}",
                QuoteString(repo),
                QuoteString(enabled_rx),
                services_concat_string,
            )
        else:
            yield make_formatted_string_command(
                "s6 set {0} {1}", enabled_subcommand, services_concat_string
            )

    elif enabled is False:
        if repo and set:
            yield make_formatted_string_command(
                "s6-rc-set-change -r {0} {1} {2} {3}",
                QuoteString(repo),
                QuoteString(set),
                QuoteString(disabled_rx),
                services_concat_string,
            )
        elif not repo and set:
            yield make_formatted_string_command(
                "s6-rc-set-change {0} {1} {2}",
                QuoteString(set),
                QuoteString(disabled_rx),
                services_concat_string,
            )
        elif repo and not set:
            yield make_formatted_string_command(
                "s6-rc-set-change -r {0} current {1} {2}",
                QuoteString(repo),
                QuoteString(disabled_rx),
                services_concat_string,
            )
        else:
            yield make_formatted_string_command(
                "s6 set {0} {1}", disabled_subcommand, services_concat_string
            )
