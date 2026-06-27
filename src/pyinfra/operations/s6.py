"""Manage s6-rc services (https://www.skarnet.org/software/s6-rc/)."""

from operator import itemgetter
from collections.abc import Iterable

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

    all_status = host.get_fact(S6LiveStatus).data
    # Tuple[bool] of status of each service in services arg
    specified_status = (
        itemgetter(*services)(all_status) if len(all_status) != 1 else (all_status[services[0]]),
    )
    all_running = True if all(specified_status) else False
    # all_running = True if all(itemgetter(*services)(all_status)) else False

    services_concat_string = QuoteString(" ".join(services))

    # breakpoint()

    # ===
    # idempotency logic
    # ===

    if not running:
        if all_running:
            yield make_formatted_string_command("s6 live stop {0}", services_concat_string)
        elif len(services) == 1:
            host.noop(f"service {' '.join(services)} is stopped")
        else:
            host.noop(f"services {' '.join(services)} are stopped")

    if running:
        if not all_running:
            yield make_formatted_string_command("s6 live start {0}", services_concat_string)
        elif len(services) == 1:
            host.noop(f"service {' '.join(services)} is running")
        else:
            host.noop(f"service {' '.join(services)} are running")

    # TODO if restart requested, only restart the already running services
    if restarted and all_running:
        yield make_formatted_string_command("s6 live restart {0}", services_concat_string)

    if reloaded and all_running:
        yield make_formatted_string_command(
            "s6 process kill -s {0} {1}", reload_signal, services_concat_string
        )

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
