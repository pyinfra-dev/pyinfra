"""Manage s6-rc services (https://www.skarnet.org/software/s6-rc/)."""

import os
import builtins
import re
from collections.abc import Iterable

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, OperationError, OperationValueError, operation
from pyinfra.api.command import make_formatted_string_command
from pyinfra.facts.s6 import S6LiveStatus, S6SetStatus
from pyinfra.facts.files import FindInFile, Directory
from pyinfra.operations import files
from pyinfra.operations.files import _raise_or_remove_invalid_path

# https://skarnet.org/software/execline/envfile.html#syntax
_repodir_pattern = re.compile(r'^\s*repodir\s*=\s*(/[^\s]*|"/.*")\s*$')


def _make_format_fields(n):
    """Returns "{0} {1} ... {n}"."""
    return " ".join([f"{{{i}}}" for i in range(n)])


def _make_live_command(op: str, services: Iterable):
    """
    + op: the operation, e.g. "start", "stop", "restart".
    + services: the service(s) to operate on.
    """
    return make_formatted_string_command(
        f"s6 live {op} " + _make_format_fields(len(services)), *map(QuoteString, services)
    )


def _make_rx_command(services: list, current_rxs: dict, wanted_rx: str):
    """Returns a command like "s6 set enable httpd".

    + services: the services to be assigned a specific prescription.
    + current_rxs: the current prescriptions for all services (from the S6SetStatus fact).
    + wanted_rx: the prescription to assign to each service.

    If every service already matches the desired prescription, None is returned.
    """
    # services that need their prescription changed (not all of them; those that are already in the
    # desired state are not in this list)
    service_subset = []

    for srv in services:
        try:
            if current_rxs[srv] != wanted_rx:
                service_subset.append(srv)
        except KeyError:
            service_subset.append(srv)

    if service_subset:
        _rx_to_subcommand = {
            "always": "make-essential",
            "active": "enable",
            "usable": "disable",
            "masked": "mask",
        }

        op = _rx_to_subcommand[wanted_rx]
        return make_formatted_string_command(
            f"s6 set {op} " + _make_format_fields(len(service_subset)),
            *map(QuoteString, service_subset),
        )
    else:
        return None


def _make_rx_commands(prescriptions: dict, name: str = "current", force_prescriptions: bool = True):
    """Returns all commands necessary to bring the prescriptions to the desired state.

    + prescriptions: map of service -> prescription, which is one of "always", "active", "usable", "masked"
    + name: name of the set to change prescriptions for.
    + force_prescriptions: whether to ensure there are no other services in the set or to only modify the prescriptions of the specified services, leaving others untouched.

    Returns a length-4 array of `StringCommand`s or `None`s, for each prescription type, depending
    on whether any services needed to be switched to that prescription. This is essentially 4
    invocations of `_make_rx_command` for each type of prescription.
    """

    _working_rx_set = builtins.set(prescriptions.values())
    if not _working_rx_set <= {"always", "active", "usable", "masked"}:
        raise OperationValueError(
            'prescriptions must be one of "always", "active", "usable", or "masked"'
        )

    # bin services by desired prescription
    service_bins = {
        "wanted_always": [],
        "wanted_active": [],
        "wanted_usable": [],
        "wanted_masked": [],
    }

    if "always" in _working_rx_set:
        service_bins["wanted_always"].extend(
            [srv for srv in prescriptions if prescriptions[srv] == "always"]
        )
    if "active" in _working_rx_set:
        service_bins["wanted_active"].extend(
            [srv for srv in prescriptions if prescriptions[srv] == "active"]
        )
    if "usable" in _working_rx_set:
        service_bins["wanted_usable"].extend(
            [srv for srv in prescriptions if prescriptions[srv] == "usable"]
        )
    if "masked" in _working_rx_set:
        service_bins["wanted_masked"].extend(
            [srv for srv in prescriptions if prescriptions[srv] == "masked"]
        )

    current_rxs = host.get_fact(S6SetStatus, name)

    if force_prescriptions:
        # mask all services not present in `prescriptions` arg
        service_bins["wanted_masked"].extend(
            [srv for srv in current_rxs if srv not in prescriptions]
        )

    return [
        _make_rx_command(service_set, current_rxs, wanted_rx.removeprefix("wanted_"))
        for wanted_rx, service_set in service_bins.items()
    ]


@operation(is_idempotent=False)
def set_delete(names: str | Iterable[str]):
    """Delete sets.

    + names: name or list of names of the sets to delete.
    """
    if isinstance(names, str):
        names = (names,)

    # TODO use _make_format_fields
    # s = " ".join([f"{{{i}}}" for i in range(len(names))])
    yield make_formatted_string_command(
        "s6 set delete " + _make_format_fields(len(names)), *map(QuoteString, names)
    )


# maybe it is idempotent?
@operation(is_idempotent=False)
def set_save(name: str, force: bool = False, force_backup: bool = True):
    """Save the current working set.

    + name: name to save the current working set as.
    + force: whether to overwrite an existing set of the same name if it exists.
    + force_backup: whether to backup an existing set that would be overwritten by `force`.
    """
    if force:
        if force_backup:
            # requires knowing path of the repository.
            # regex will break if repodir key pair in /etc/s6-frontend.conf spans several lines.
            lines = host.get_fact(
                FindInFile,
                "/etc/s6-frontend.conf",
                r"repodir\s*=",
                interpolate_variables=False,
                extended_regex=True,
            )
            if lines is None:
                raise OperationError(
                    "no repodir found in /etc/s6-frontend.conf, or file doesn't exist"
                )
            if len(lines) != 1:
                # no OperationWarning
                raise RuntimeWarning(
                    "multiple repodir definitions found in /etc/s6-frontend.conf, using the first one"
                )
            if (m := _repodir_pattern.fullmatch(lines[0])) is None:
                raise OperationError("failed to match repodir line in /etc/s6-frontend.conf")
            repodir = m[1]

            if host.get_fact(Directory, os.path.join(repodir, name)):
                yield from _raise_or_remove_invalid_path(
                    "directory", os.path.join(repodir, name), True, True, False
                )

            # no -f since the old set has already been moved
            yield make_formatted_string_command("s6 set save {0}", QuoteString(name))

        # force_save=True, backup=False
        else:
            yield make_formatted_string_command("s6 set save -f {0}", QuoteString(name))

    # save=True, force_save=False
    else:
        yield make_formatted_string_command("s6 set save {0}", QuoteString(name))


@operation(is_idempotent=False)
def set_commit():
    """Check the current working set and commit it."""
    yield StringCommand("s6 set check -F")
    yield StringCommand("s6 set commit")


@operation(is_idempotent=False)
def live_install():
    """Install the compiled (committed) service database into the live state."""
    yield StringCommand("s6 live install")


# TODO support for repositories other than the one in s6-frontend.conf (e.g. a user repository for
# user services)
@operation(
    is_idempotent=False,
    # TODO verify
    # when the_set is not "current", always executes `s6 set load [the_set]`
    # force_backup idempotent?
    # force_save idempotent?
    idempotent_notice='Not idempotent by default. If any of the following are true, then idempotency is broken: `the_set != "current", `do_commit=True`',
)
def set(
    the_set: str = "current",
    prescriptions: dict[str] | None = None,
    force_prescriptions: bool = True,
    present: bool = True,
    do_save: bool = False,
    save_as: str | None = None,
    force_save: bool = False,
    force_backup: bool = True,
    do_commit: bool = True,
    # TODO configurable s6-frontend.conf location
):
    """
    Manage sets in a repository.

    + the_set: name of the set to manage.
    + prescriptions: the prescriptions to ensure in the set. A map of service name -> prescription, where the prescription is any of "always", "active", "usable", "masked". May be `None`, which allows management of set presence only.
    + force_prescriptions: whether the `prescriptions` should be the *only* prescriptions in the set (i.e. other services will be removed)
    + present: whether the set should be present in the repository.
    + do_save: whether to save the set to the repository.
    + save_as: name for the saved set. required if `do_save` is True.
    + force_save: whether to overwrite existing sets.
    + force_backup: whether to backup overwritten sets by appending the timestamp to the directory name. only works with `force_save`.
    + do_commit: whether to commit the current(ly loaded) set. delaying this step can allow for other operations to modify the current set, with the final result being committed at the end.

    """

    if present:
        # deleting noops from the set if they don't occur cleans up conditionals, not requiring else clauses
        noops = {"prescribe", "save", "commit"}
        if prescriptions:
            if any(
                cmds := _make_rx_commands(
                    prescriptions, the_set, True if force_prescriptions else False
                )
            ):
                noops.remove("prescribe")
                if the_set != "current":
                    yield make_formatted_string_command("s6 set load {0}", QuoteString(the_set))
                yield from filter(lambda cmd: cmd is not None, cmds)

        if do_save:
            if not save_as:
                raise OperationValueError(
                    "saving a set requires a name to save it under (do_save => save_as)"
                )
            # when the current set matches an existing named set exactly, noop
            if not host.get_fact(S6SetStatus, save_as) == host.get_fact(S6SetStatus, "current"):
                noops.remove("save")
                if the_set != "current":
                    yield make_formatted_string_command("s6 set load {0}", QuoteString(the_set))
                if force_save:
                    if force_backup:
                        yield from set_save._inner(save_as, True, True)
                    else:
                        yield from set_save._inner(save_as, True, False)
                else:
                    yield from set_save._inner(save_as, False, False)

        # non-idempotent
        if do_commit:
            noops.remove("commit")
            yield from set_commit._inner()

        # "global" noop if all 3 branches noop
        if noops == {"prescribe", "save", "commit"}:
            if prescriptions and not do_save:
                host.noop('the set "current" already has the desired prescriptions')
            elif do_save:
                host.noop(f'the set "current" already has the desired prescriptions and matches with the existing set "{save_as}"')
            else:
                host.noop(f'the set "{the_set}" already exists')

    # present=False
    else:
        if host.get_fact(S6SetStatus, the_set):
            yield make_formatted_string_command("s6 set delete {0}", QuoteString(the_set))
        else:
            host.noop(f'the set "{the_set}" already doesn\'t exist')


@operation(
    is_idempotent=False,
    idempotent_notice="It is not idempotent only when at least one of `commit_set` or `install_set` are `True`.",
)
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
    + command: custom command to run after the auto-computed commands. This must be an s6 subcommand, e.g. "system reboot" gives the command "s6 system reboot".
    + enabled: whether the service should be given an "active" or "usable" prescription
    + reload_signal: the signal to send to the service(s) when a reload is desired.
    + repo: name of the repository to use when managing enabled status, using the one configured in s6-frontend.conf by default.
    + the_set: name of the set to use when managing enabled status, using the set named "current" by default.
    + enabled_rx: name of the prescription to assign to the service(s) when enabled, which could be either "active" or "always"
    + disabled_rx: name of the prescription to assign to the service(s) when disabled, which could be either "usable" or "masked"
    + commit_set: whether to commit the current(ly loaded) set. Delaying this step can allow for other operations to modify the current set, with the final result being committed at the end.
    + install_set: whether to install the compiled service database (the result of a commit operation) into the live state. This is analagous to systemd's daemon-reload, but not completely: systemd recognizes changes to service files after a reboot, but s6 does not. It only recognizes changes when an s6 live install command is executed. Live state replacement and enablement/disablement of services are coupled in s6.

    Specifying multiple services results in fewer commands executed, especially in the case of
    changing the enabled status of the service, where the service database is recompiled per
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

    if (running, restarted, reloaded) != (None,) * 3:
        # dict[str, bool] whether the services given in the services arg are running.
        live_statuses = {srv: host.get_fact(S6LiveStatus)[srv] for srv in service}
        all_up = all(live_statuses.values())
        some_up = any(live_statuses.values())
        all_down_services = [srv for srv, stat in live_statuses.items() if not stat]
        all_up_services = [srv for srv, stat in live_statuses.items() if stat]

        if running is False:
            if some_up:
                yield _make_live_command("stop", all_up_services)
            else:
                host.noop(f"all specified services are already down: {service}")

        if running is True:
            if not all_up:
                yield _make_live_command("start", all_down_services)
            else:
                host.noop(f"all specified services are already up: {service}")

        if restarted:
            if some_up:
                yield _make_live_command("restart", all_up_services)
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
    if enabled is not None:
        if enabled is True:
            yield from set._inner(
                the_set=the_set, prescriptions={srv: enabled_rx for srv in service}
            )

        if enabled is False:
            yield from set._inner(
                the_set=the_set, prescriptions={srv: disabled_rx for srv in service}
            )

        # s6.set operation already handles s6 set load
        if commit_set:
            yield from set_commit._inner()
            if install_set:
                yield from live_install._inner()

    if command:
        yield make_formatted_string_command("s6 {0}", command)
