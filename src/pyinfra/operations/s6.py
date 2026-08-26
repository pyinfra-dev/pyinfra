"""Manage s6-rc services (https://www.skarnet.org/software/s6-rc/)."""

import os
import re
import shlex
from collections.abc import Sequence

from pyinfra import host, logger
from pyinfra.api import (
    QuoteString,
    StringCommand,
    OperationError,
    OperationValueError,
    operation,
    Host,
)
from pyinfra.api.command import make_formatted_string_command
from pyinfra.facts.s6 import S6LiveStatus, S6SetStatus, S6RepositoryList
from pyinfra.facts.files import FindInFile, Directory, File, FileContents
from pyinfra.facts.server import Command
from pyinfra.operations.files import _raise_or_remove_invalid_path

# https://skarnet.org/software/execline/envfile.html#syntax
_repodir_pattern = re.compile(r'^\s*repodir\s*=\s*(/[^\s]*|"/.*")\s*$')


def _get_repodir_from_conf(content: list[str]):
    """Get the path to a repodir from an s6 configuration file.

    + content: the text in the file, with each line being a string in the list.
    """
    # simplistic check for now, avoiding complicated syntax
    # does not account for a statement broken over multiple lines with backslashes
    # assume repodir line is unique
    if match := re.search(
        r'^\s*repodir\s*=\s*(/[^\s]*|"/.*")\s*$', "\n".join(content), re.MULTILINE
    ):
        return match.group(1)

    return

    ## TODO edge case
    # for line, next_line in itertools.pairwise(content):
    #    # ignore commented, empty and whitespace lines
    #    if line == "":
    #        continue
    #    elif re.search(r'^\s*#', line, re.ASCII):
    #        continue
    #    elif re.fullmatch(r'\s+', line, re.ASCII):
    #        continue

    #    # line continuation detected
    #    if line.endswith("\\"):
    #        if next_line.endswith("\\"):
    #            pass
    #    elif "=" not in line:
    #        return False


def _s6_repo_lookup(host: Host):
    """Attempts to find an s6-rc repository.

    The algorithm is as follows:

    The environment variable `S6_CONF` is checked for a valid filesystem path, and if it is, check
    whether the file defines a repodir. Otherwise check whether the file `/etc/s6.conf` exists and
    if it defines a repodir. If both fail, no value is returned.
    """
    conf_envvar = host.get_fact(Command, 'printf %s "$S6_CONF"')

    if conf_envvar != "":
        conf = host.get_fact(FileContents, conf_envvar)
        if repodir := _get_repodir_from_conf(conf):
            return repodir

    if s6_conf := host.get_fact(FileContents, "/etc/s6.conf"):
        if repodir := _get_repodir_from_conf(s6_conf):
            return repodir

    # for compatibility with older versions of s6-frontend. the envvar used to have a different name
    # and config file was called something else.
    conf_envvar_old = host.get_fact(Command, 'printf %s "$S6_FRONTEND_CONF"')

    if conf_envvar_old != "":
        conf = host.get_fact(FileContents, conf_envvar_old)
        if repodir := _get_repodir_from_conf(conf):
            return repodir

    if frontend_conf := host.get_fact(FileContents, "/etc/s6-frontend.conf"):
        if repodir := _get_repodir_from_conf(frontend_conf):
            return repodir

    return


def _make_format_fields(n):
    """Returns "{0} {1} ... {n-1}"."""
    return " ".join([f"{{{i}}}" for i in range(n)])


def _make_live_command(op: str, services: Sequence):
    """
    + op: the operation, e.g. "start", "stop", "restart".
    + services: the service(s) to operate on.
    """
    return make_formatted_string_command(
        f"s6 live {op} " + _make_format_fields(len(services)), *map(QuoteString, services)
    )


def _make_rx_command(services: list, current_rxs: dict, wanted_rx: str, the_set: str = "current"):
    """Returns a command like "s6 set enable httpd".

    + services: the services to be assigned a specific prescription.
    + current_rxs: the current prescriptions for all services (from the S6SetStatus fact).
    + wanted_rx: the prescription to assign to each service.
    + the_set: name of the set to operate on

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

        # example of the string passed into make_formatted_string_command
        # s6 set disable -s {5} {0} {1} {2} {3} {4}
        op = _rx_to_subcommand[wanted_rx]
        return make_formatted_string_command(
            f"s6 set {op} -s {{{len(service_subset)}}} " + _make_format_fields(len(service_subset)),
            *map(QuoteString, service_subset),
            QuoteString(the_set),
        )
    else:
        return None


def _make_rx_commands(
    prescriptions: dict, the_set: str = "current", force_prescriptions: bool = True
):
    """Returns all commands necessary to bring the prescriptions to the desired state.

    + prescriptions: map of service -> prescription, which is one of "always", "active", "usable", "masked"
    + name: name of the set to change prescriptions for.
    + force_prescriptions: whether to ensure there are no other services in the set or to only modify the prescriptions of the specified services, leaving others untouched.

    Returns a length-4 array of `StringCommand`s or `None`s, for each prescription type, depending
    on whether any services needed to be switched to that prescription. This is essentially 4
    invocations of `_make_rx_command` for each type of prescription.
    """

    _working_rx_set = set(prescriptions.values())
    if not _working_rx_set <= {"always", "active", "usable", "masked"}:
        raise OperationValueError(
            'prescriptions must be one of "always", "active", "usable", or "masked"'
        )

    # bin services by desired prescription
    service_bins: dict[str, list[str]] = {
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

    current_rxs = host.get_fact(S6SetStatus, the_set)

    if force_prescriptions:
        # mask all services not present in `prescriptions` arg
        service_bins["wanted_masked"].extend(
            [srv for srv in current_rxs if srv not in prescriptions]
        )

    return [
        _make_rx_command(
            service_set, current_rxs, wanted_rx.removeprefix("wanted_"), the_set=the_set
        )
        for wanted_rx, service_set in service_bins.items()
    ]


@operation(is_idempotent=False)
def set_create(name: str, repository: str | None = None):
    """Create a new set.

    + name: name for the new set.
    + repository: repository to save the set in.

    This is a distinct operation from set_copy.
    """
    if repository:
        existing_sets = host.get_fact(S6RepositoryList, repository=repository)
        if name not in existing_sets:
            yield make_formatted_string_command(
                "s6-rc-set-new -r {0} {1}", QuoteString(repository), QuoteString(name)
            )

    elif repodir := _s6_repo_lookup(host):
        existing_sets = host.get_fact(S6RepositoryList, repository=repodir)
        if name not in existing_sets:
            yield make_formatted_string_command(
                "s6-rc-set-new -r {0} {1}", QuoteString(repodir), QuoteString(name)
            )
    # fallback to compiled-in default repo, which is /var/lib/s6/repository if left unchanged at
    # compile time
    else:
        yield make_formatted_string_command("s6-rc-set-new {0}", QuoteString(name))


@operation(is_idempotent=False)
def set_delete(names: str | Sequence[str]):
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


@operation(is_idempotent=False)
def set_copy(dest: str, source="current", force: bool = False):
    """Save the contents of the given set as a new set.

    + dest: name of the saved copy.
    + source: name of the set to copy.
    + force: whether to overwrite an existing set of the same name if it exists.
    """
    if force:
        yield make_formatted_string_command(
            "s6 set copy -f {0} {1}", QuoteString(source), QuoteString(dest)
        )

        # backing up requires more thought. try to use $S6_FRONTEND_CONF, envfile, and whether the
        # fact that the friendly set names are symlinks to unique names changes anything
        # (e.g. `readlink /etc/s6/repo/sources/default` gives `.default:YN2tP3`).

        # + force_backup: whether to backup an existing set that would be overwritten by `force`.
        # if force_backup:
        #    # requires knowing path of the repository.
        #    # regex will break if repodir key pair in /etc/s6-frontend.conf spans several lines.
        #    lines = host.get_fact(
        #        FindInFile,
        #        "/etc/s6-frontend.conf",
        #        r"repodir\s*=",
        #        interpolate_variables=False,
        #        extended_regex=True,
        #    )
        #    if lines is None:
        #        raise OperationError(
        #            "no repodir found in /etc/s6-frontend.conf, or file doesn't exist"
        #        )
        #    if len(lines) != 1:
        #        # no OperationWarning
        #        logger.warning(
        #            "multiple repodir definitions found in /etc/s6-frontend.conf, using the first one"
        #        )
        #    if (m := _repodir_pattern.fullmatch(lines[0])) is None:
        #        raise OperationError("failed to match repodir line in /etc/s6-frontend.conf")
        #    repodir = m[1]

        #    if host.get_fact(Directory, os.path.join(repodir, dest)):
        #        yield from _raise_or_remove_invalid_path(
        #            "directory", os.path.join(repodir, dest), True, True, False
        #        )

        #    # no -f since the old set has already been moved
        #    yield make_formatted_string_command(
        #        "s6 set copy {0} {1}", QuoteString(source), QuoteString(dest)
        #    )

        # force_save=True, backup=False
        # else:
        #    yield make_formatted_string_command(
        #        "s6 set copy -f {0} {1}", QuoteString(source), QuoteString(dest)
        #    )

    # save=True, force_save=False
    else:
        yield make_formatted_string_command(
            "s6 set copy {0} {1}", QuoteString(source), QuoteString(dest)
        )


@operation(is_idempotent=False)
def set_commit(the_set: str = "current"):
    """Check the given set and commit it.

    + the_set: name of the set to check and commit.
    """
    yield make_formatted_string_command("s6 set check -F -s {0}", QuoteString(the_set))
    yield make_formatted_string_command("s6 set commit -s {0}", QuoteString(the_set))


@operation(is_idempotent=False)
def live_install(the_set: str = "current"):
    """Install a compiled (committed) service database into the live state.

    + the_set: name of the set containing an already compiled service database to be installed into the live state.
    """
    yield make_formatted_string_command("s6 live install -s {0}", QuoteString(the_set))


# TODO refactor now that skarnet added -s option to many s6 frontend commands
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
def manage_set(
    the_set: str = "current",
    # no -r option exposed by s6-frontend
    # repository: str | None = None,
    prescriptions: dict[str, str] | None = None,
    force_prescriptions: bool = True,
    present: bool = True,
    do_save: bool = False,
    save_as: str | None = None,
    force_save: bool = False,
    # force_backup: bool = True,
    do_commit: bool = True,
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
    + do_commit: whether to commit the current(ly loaded) set. delaying this step can allow for other operations to modify the current set, with the final result being committed at the end.

    """
    # + force_backup: whether to backup overwritten sets by appending the timestamp to the directory name. only works with `force_save`.

    if present:
        # deleting noops from the set if they don't occur cleans up conditionals, not requiring else clauses
        noops = {"create", "prescribe", "save", "commit"}

        ### set creation ###
        # the repository needs to be the one recognized by s6-frontend, as the other sub-operations
        # use s6-frontend commands that don't have a repository option; they implicitly use the one
        # in the configuration. if the repository were able to be specified by the user here, set
        # creation could occur in a different repository than the other operations.
        if repodir := _s6_repo_lookup(host):
            existing_sets = host.get_fact(S6RepositoryList, repository=repodir)
            if the_set not in existing_sets:
                noops.remove("create")
                yield make_formatted_string_command(
                    "s6-rc-set-new -r {0} {1}", QuoteString(repodir), QuoteString(the_set)
                )

        ### prescription assignment ###
        if prescriptions:
            if any(
                cmds := _make_rx_commands(
                    prescriptions, the_set, True if force_prescriptions else False
                )
            ):
                noops.remove("prescribe")
                # _make_rx_commands should already include -s the_set, no need to load now
                # if the_set != "current":
                # yield make_formatted_string_command("s6 set load {0}", QuoteString(the_set))
                yield from filter(lambda cmd: cmd is not None, cmds)

        ### saving ###
        if do_save:
            if not save_as:
                raise OperationValueError(
                    "saving a set requires a name to save it under (do_save => save_as)"
                )
            # when the current set matches an existing named set exactly, noop
            if not host.get_fact(S6SetStatus, save_as) == host.get_fact(S6SetStatus, the_set):
                noops.remove("save")
                yield from set_copy._inner(
                    dest=save_as, source=the_set, force=True if force_save else False
                )

        ### committing ###
        # non-idempotent
        if do_commit:
            noops.remove("commit")
            yield from set_commit._inner(the_set)

        # "global" noop if all 4 branches noop
        if noops == {"create", "prescribe", "save", "commit"}:
            if prescriptions and not do_save:
                host.noop('the set "current" already has the desired prescriptions')
            elif do_save:
                host.noop(
                    f'the set "current" already has the desired prescriptions and matches with the existing set "{save_as}"'
                )
            else:
                host.noop(f'the set "{the_set}" already exists')

    ### deleting ###
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
    service: str | Sequence[str],
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

    + service: name(s) of the service(s) to manage.
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
    + install_set: whether to install the compiled service database (the result of a commit operation) into the live state. This is analogous to systemd's daemon-reload, but not completely: systemd recognizes changes to service files after a reboot, but s6 does not. It only recognizes changes when an s6 live install command is executed. Live state replacement and enablement/disablement of services are coupled in s6.

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
                host.noop(f"all specified services are already down: {', '.join(service)}")

        if running is True:
            if not all_up:
                yield _make_live_command("start", all_down_services)
            else:
                host.noop(f"all specified services are already up: {', '.join(service)}")

        if restarted:
            if some_up:
                yield _make_live_command("restart", all_up_services)
            else:
                host.noop(f"all specified services are down: {', '.join(service)}")

        if reloaded:
            if some_up:
                yield make_formatted_string_command(
                    "s6 process kill -s {0} "
                    + " ".join([f"{{{i + 1}}}" for i in range(len(all_up_services))]),
                    QuoteString(reload_signal),
                    *map(QuoteString, all_up_services),
                )
            else:
                host.noop(f"all specified services are down: {', '.join(service)}")

    # TODO: test masked services present in `services` arg on a real system
    if enabled is not None:
        if enabled is True:
            yield from manage_set._inner(
                the_set=the_set, prescriptions={srv: enabled_rx for srv in service}
            )

        if enabled is False:
            yield from manage_set._inner(
                the_set=the_set, prescriptions={srv: disabled_rx for srv in service}
            )

        # s6.set operation already handles s6 set load
        if commit_set:
            yield from set_commit._inner()
            if install_set:
                yield from live_install._inner()

    if command:
        yield StringCommand("s6", *map(QuoteString, shlex.split(command)))
