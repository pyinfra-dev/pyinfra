"""Manage s6-rc services (https://www.skarnet.org/software/s6-rc/)."""

# import re
import shlex
from collections.abc import Sequence
from typing import Literal

from pyinfra import host, logger
from pyinfra.api import (
    QuoteString,
    StringCommand,
    # OperationError,
    OperationValueError,
    operation,
)
from pyinfra.api.command import make_formatted_string_command
from pyinfra.facts.s6 import S6LiveStatus, S6SetStatus, S6RepositoryList

_rx_to_subcommand = {
    "always": "make-essential",
    "active": "enable",
    "usable": "disable",
    "masked": "mask",
}

# def _get_s6_frontend_conf_contents(host: Host) -> list[str] | None:
#     """Attempts to locate and return the contents of an s6-frontend configuration.
#
#     Does not return anything if no configuration is found.
#
#     + host: pyinfra host object on which to perform this lookup.
#     """
#     conf_envvar = host.get_fact(Command, 'printf %s "$S6_CONF"')
#     if conf_envvar != "":
#         if contents := host.get_fact(FileContents, conf_envvar):
#             return contents
#
#     if contents := host.get_fact(FileContents, "/etc/s6.conf"):
#         return contents
#
#     return None


# def _get_value_from_conf(key: str, content: list[str] | None) -> str | None:
#     """Get the value associated with a key in an s6-frontend configuration.
#
#     If no repodir is found, nothing is returned.
#
#     + key: the key associated with the value, e.g. "repodir".
#     + content: the file contents, as a list of strings. if `None`, this function returns nothing.
#     """
#     # simplistic check for now, avoiding complicated syntax
#     # does not account for a statement broken over multiple lines with backslashes
#     # assume the key is unique
#     if content is not None:
#         if match := re.search(
#             # https://skarnet.org/software/execline/envfile.html#syntax
#             r"^\s*" + re.escape(key) + r'\s*=\s*(/[^\s]*|"/.*")\s*$',
#             "\n".join(content),
#             re.MULTILINE,
#         ):
#             return match.group(1)
#
#     return None

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


# def _s6_frontend_repo_lookup(host: Host):
#    """Attempts to find an s6-rc repository.
#
#    The algorithm is as follows:
#
#    The environment variable `S6_CONF` is checked for a valid filesystem path, and if it is, check
#    whether the file defines a repodir. Otherwise check whether the file `/etc/s6.conf` exists and
#    if it defines a repodir. If both fail, no value is returned.
#    """
#    conf_envvar = host.get_fact(Command, 'printf %s "$S6_CONF"')
#
#    if conf_envvar != "":
#        conf = host.get_fact(FileContents, conf_envvar)
#        if repodir := _get_repodir_from_conf(conf):
#            return repodir
#
#    if s6_conf := host.get_fact(FileContents, "/etc/s6.conf"):
#        if repodir := _get_repodir_from_conf(s6_conf):
#            return repodir
#
#    # for compatibility with older versions of s6-frontend. the envvar used to have a different name
#    # and config file was called something else.
#    conf_envvar_old = host.get_fact(Command, 'printf %s "$S6_FRONTEND_CONF"')
#
#    if conf_envvar_old != "":
#        conf = host.get_fact(FileContents, conf_envvar_old)
#        if repodir := _get_repodir_from_conf(conf):
#            return repodir
#
#    if frontend_conf := host.get_fact(FileContents, "/etc/s6-frontend.conf"):
#        if repodir := _get_repodir_from_conf(frontend_conf):
#            return repodir
#
#    return


def _make_format_fields(n):
    """Returns "{0} {1} ... {n-1}"."""
    return " ".join([f"{{{i}}}" for i in range(n)])


def _make_live_change_command(op: str, services: Sequence, livedir: str | None = None):
    """
    + op: the operation, e.g. "start", "stop", "restart".
    + services: the service(s) to operate on.
    """
    # fall back to s6-rc cli that allows a custom livedir
    if livedir:
        if op == "restart":
            return make_formatted_string_command(
                f"s6-rc -l {{{len(services)}}} -d change "
                + _make_format_fields(len(services))
                + f" && s6-rc -l {{{len(services)}}} -u change "
                + _make_format_fields(len(services)),
                *map(QuoteString, services),
                QuoteString(livedir),
            )
        # translate s6 frontend arguments to s6-rc arguments
        op = "-u" if op == "start" else "-d"
        return make_formatted_string_command(
            f"s6-rc -l {{{len(services)}}} {op} change " + _make_format_fields(len(services)),
            *map(QuoteString, services),
            QuoteString(livedir),
        )

    return make_formatted_string_command(
        f"s6 live {op} " + _make_format_fields(len(services)), *map(QuoteString, services)
    )


def _make_set_change_command(
    services: list,
    current_rxs: dict,
    wanted_rx: str,
    repodir: str | None = None,
    the_set: str = "current",
):
    """Returns a command like "s6-rc-set-change -r /etc/s6/repo -p current active httpd".

    + services: the services to be assigned a specific prescription.
    + current_rxs: the current prescriptions for all services (from the `S6SetStatus` fact).
    + wanted_rx: the prescription to assign to each service.
    + repodir: path to the repository containing the set. If None, will use s6-frontend to autodiscover the repodir.
    + the_set: name of the set to operate on.

    If every service already matches the desired prescription, None is returned.
    """
    if wanted_rx not in {"always", "active", "usable", "masked"}:
        raise ValueError(
            f'wanted_rx must be one of "always", "active", "usable", or "masked", got {wanted_rx}.'
        )

    # services that need their prescription changed (not all of them; those that are already in the
    # desired state are excluded from this list)
    service_subset = []

    for srv in services:
        try:
            if current_rxs[srv] != wanted_rx:
                service_subset.append(srv)
        except KeyError:
            service_subset.append(srv)

    if service_subset:
        # example of the string passed into make_formatted_string_command:
        # s6-rc-set-change -r {5} {6} usable {0} {1} {2} {3} {4}
        # NOTE: because -p (--pull-dependencies) is used, enabling a set of services then disabling
        # the same set of services (without using force_prescriptions) will likely leave the system
        # in a different state than before, as several dependent services may still be in the
        # altered state.
        if repodir:
            return make_formatted_string_command(
                f"s6-rc-set-change -r {{{len(service_subset)}}} -p {{{len(service_subset) + 1}}} {wanted_rx} "
                + _make_format_fields(len(service_subset)),
                *map(QuoteString, service_subset),
                QuoteString(repodir),
                QuoteString(the_set),
            )

        return make_formatted_string_command(
            f"s6 set {_rx_to_subcommand[wanted_rx]} -p -s {{{len(service_subset)}}} "
            + _make_format_fields(len(service_subset)),
            *map(QuoteString, service_subset),
            QuoteString(the_set),
        )

    return None


def _make_all_set_change_commands(
    prescriptions: dict,
    repodir: str | None = None,
    the_set: str = "current",
    # force_prescriptions: bool = True,
):
    """Returns all commands necessary to bring the prescriptions to the desired state.

    + prescriptions: map of service -> prescription, which is one of "always", "active", "usable", "masked". If this is set to `False`, all services will be masked.
    + repodir: path to a repository containing the set.
    + the_set: the set to change the prescriptions of.

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

    current_rxs = host.get_fact(S6SetStatus, the_set, repodir)

    # if force_prescriptions:
    #     # mask all services not present in `prescriptions` arg
    #     service_bins["wanted_masked"].extend(
    #         [srv for srv in current_rxs if srv not in prescriptions]
    #     )

    if prescriptions == {}:
        return [None] * 3 + [
            _make_set_change_command(
                list(current_rxs.keys()), current_rxs, "masked", repodir, the_set=the_set
            )
        ]

    return [
        _make_set_change_command(
            service_set, current_rxs, wanted_rx.removeprefix("wanted_"), repodir, the_set=the_set
        )
        for wanted_rx, service_set in service_bins.items()
    ]


# TODO there is no s6-frontend command equivalent to create a set (only copy,
# at the time of writing), so repodir must be given or it will fall back to
# compiled-in default, not the frontend-configured repodir
@operation(is_idempotent=False)
def set_create(name: str, repodir: str | None = None):
    """Create a new set.

    + name: name for the new set.
    + repodir: path to the repository to save the set in.
    """
    if repodir:
        yield make_formatted_string_command(
            "s6-rc-set-new -r {0} {1}", QuoteString(repodir), QuoteString(name)
        )
    else:
        yield make_formatted_string_command("s6-rc-set-new {0}", QuoteString(name))


@operation(is_idempotent=False)
def set_delete(the_sets: str | Sequence[str], repodir: str | None = None):
    """Delete sets.

    + the_sets: name or list of names of the sets to delete.
    + repodir: path to the repository containing the sets
    """
    if isinstance(the_sets, str):
        the_sets = (the_sets,)

    if "current" in the_sets:
        raise OperationValueError('cannot delete the set "current"')

    if repodir:
        yield make_formatted_string_command(
            f"s6-rc-set-delete -r {{{len(the_sets)}}} " + _make_format_fields(len(the_sets)),
            *map(QuoteString, the_sets),
            QuoteString(repodir),
        )
    else:
        yield make_formatted_string_command(
            "s6-rc-set-delete " + _make_format_fields(len(the_sets)), *map(QuoteString, the_sets)
        )


@operation()
def set_copy(dest: str, repodir: str | None = None, source="current", force: bool = False):
    """Save the contents of the given set as a new set.

    + dest: name of the saved copy.
    + repodir: path to the repository containing the set.
    + source: name of the set to copy.
    + force: whether to overwrite an existing set of the same name if it exists.
    """
    source_set_contents = host.get_fact(S6SetStatus, the_set=source, repodir=repodir)
    dest_set_contents = host.get_fact(S6SetStatus, the_set=dest, repodir=repodir)
    if source_set_contents != dest_set_contents:
        if repodir:
            yield make_formatted_string_command(
                f"s6-rc-set-copy -r {{0}}{' -f' if force else ''} {{1}} {{2}}",
                QuoteString(repodir),
                QuoteString(source),
                QuoteString(dest),
            )
        else:
            yield make_formatted_string_command(
                f"s6-rc-set-copy{' -f' if force else ''} {{0}} {{1}}",
                QuoteString(source),
                QuoteString(dest),
            )
    else:
        host.noop(f'the set "{dest}" exists and is identical to "{source}"')

    # TODO
    # backing up a set when it would have been overwritten by -f requires more thought. try to use
    # $S6_CONF, envfile, and whether the fact that the friendly set names are symlinks to unique
    # names changes anything (e.g. `readlink /etc/s6/repo/sources/default` gives `.default:YN2tP3`).

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


@operation(is_idempotent=False)
def set_commit(repodir: str | None = None, the_set: str = "current"):
    """Check the given set and commit it.

    + repodir: path to the repository containing the set.
    + the_set: name of the set to check and commit.
    """
    if repodir is not None:
        yield make_formatted_string_command(
            "s6-rc-set-fix -r {0} {1}", QuoteString(repodir), QuoteString(the_set)
        )
        yield make_formatted_string_command(
            "s6-rc-set-commit -r {0} {1}", QuoteString(repodir), QuoteString(the_set)
        )
    else:
        yield make_formatted_string_command("s6-rc-set-fix {0}", QuoteString(the_set))
        yield make_formatted_string_command("s6-rc-set-commit {0}", QuoteString(the_set))


@operation(is_idempotent=False)
def live_install(repodir: str | None = None, the_set: str = "current", livedir: str | None = None):
    """Install a compiled (committed) service database into the live state.

    + repodir: path to the repository containing the set.
    + the_set: name of the set containing an already compiled service database to be installed into the live state.
    + livedir: path to the live state to manage. Uses the one configured for s6-frontend by default.
    """
    if repodir:
        if livedir:
            yield make_formatted_string_command(
                "s6-rc-set-install -r {0} -l {1} {2}",
                QuoteString(repodir),
                QuoteString(livedir),
                QuoteString(the_set),
            )
        else:
            yield make_formatted_string_command(
                "s6-rc-set-install -r {0} {1}", QuoteString(repodir), QuoteString(the_set)
            )
    elif livedir:
        yield make_formatted_string_command(
            "s6-rc-set-install -l {0} {1}", QuoteString(livedir), QuoteString(the_set)
        )
    else:
        yield make_formatted_string_command("s6 live install -s {0}", QuoteString(the_set))


@operation(
    is_idempotent=False,
    idempotent_notice="Idempotent so long as `do_commit in {False, None}` and `do_install=False`.",
)
def manage_set(
    the_set: str = "current",
    present: bool = True,
    prescriptions: Literal[False] | dict[str, str] | None = None,
    # force_prescriptions: bool = True,
    do_commit: bool = False,
    do_install: bool = False,
    repodir: str | None = None,
    livedir: str | None = None,
):
    """Manage sets in a repository.

    .. important::
        This operation is in alpha. Things may break if you use it. Additionally, there is no
        support for bundles at this time; manage them at your own risk.

    `manage_set` combines smaller operations into one:
        + ensuring existence or non-existence of sets, like `files.file` does
        + ensuring specific prescriptions for subsets of services within sets
        + committing a set, which is a stateless operation
        + installing a set, which is a stateless operation

    Due to the stateless nature of commit and install, those execution paths are disabled by default.

    + the_set: name of the set to manage.
    + present: whether the set should be present in the repository.
    + prescriptions: the prescriptions to ensure in the set. A map of service name -> prescription, where the prescription is any of "always", "active", "usable", "masked". May be `None`, which allows management of set presence only. If `prescriptions=False`, then all services will be masked.
    + do_commit: whether to compile a new service database from `the_set` after changing the prescriptions of the service(s) in `the_set`. Default is not to commit.
    + do_install: whether to install the set to the livedir.
    + repodir: path to the repository to manage. Uses the one configured for `s6-frontend` by default.
    + livedir: path to the live state to install a set to when `do_install=True`.
    """

    # automatically find the configured s6-frontend repository to use in commands. the value can be
    # `None`, which happens when no configuration file was found. in this case, s6 commands will use
    # the compiled-in default repository.
    # s6_conf_lines = _get_s6_frontend_conf_contents(host)
    # if s6_conf_lines is None:
    #     # TODO should it really be a warning instead of info?
    #     logger.warning(
    #         "could not find an s6-frontend configuration on remote host, will use compiled-in default repository for s6 commands"
    #     )
    # elif s6_conf_lines == []:
    #     logger.warning(
    #         "remote host's s6-frontend configuration is an empty file, will use compiled-in default repository for s6 commands"
    #     )
    # # repodir will be `None` if not found, but possibility of None is handled, resulting in the
    # # compiled-in default repository being used.
    # repodir = _get_value_from_conf(key="repodir", content=s6_conf_lines)

    # if not (repodir := _get_value_from_conf(key="repodir", content=s6_conf_lines)):
    #    raise OperationError(
    #        f"failed to extract a repodir from remote s6-frontend config: {s6_conf_lines}"
    #    )

    logger.warning("The `s6.manage_set` operation is in alpha!")

    if present:
        # remove noops from this set as conditions are satisfied
        noops = {"create", "prescribe", "commit", "install"}

        # create a new set if it doesn't exist
        existing_sets = host.get_fact(S6RepositoryList, repodir=repodir)
        if the_set not in existing_sets:
            noops.remove("create")
            if repodir is not None:
                yield make_formatted_string_command(
                    "s6-rc-set-new -r {0} {1}", QuoteString(repodir), QuoteString(the_set)
                )
            else:
                yield make_formatted_string_command("s6-rc-set-new {0}", QuoteString(the_set))

        if prescriptions is not None:
            if prescriptions is False:
                noops.remove("prescribe")
                cmds = _make_all_set_change_commands({}, repodir, the_set=the_set)
                yield from filter(lambda cmd: cmd is not None, cmds)
            elif any(
                cmds := _make_all_set_change_commands(
                    prescriptions,
                    repodir,
                    the_set=the_set,  # , force_prescriptions=force_prescriptions
                )
            ):
                noops.remove("prescribe")
                yield from filter(lambda cmd: cmd is not None, cmds)

        # non-idempotent, I don't know of a way of checking whether the to-be compiled database
        # matches the existing compiled service database
        if do_commit:
            noops.remove("commit")
            yield from set_commit._inner(repodir=repodir, the_set=the_set)

        if do_install:
            noops.remove("install")
            yield from live_install._inner(repodir=repodir, the_set=the_set, livedir=livedir)

        # "global" noop if all 3 branches noop
        if noops == {"create", "prescribe", "commit", "install"}:
            host.noop(
                f'the set "{the_set}" already exists, has the desired prescriptions, and no commit was requested'
            )

    # present=False
    else:
        if the_set in host.get_fact(S6RepositoryList, repodir=repodir):
            if repodir is not None:
                yield make_formatted_string_command(
                    "s6-rc-set-delete -r {0} {1}", QuoteString(repodir), QuoteString(the_set)
                )
            else:
                yield make_formatted_string_command("s6-rc-set-delete {0}", QuoteString(the_set))
        else:
            host.noop(f'the set "{the_set}" is already nonexistent')


@operation(
    is_idempotent=False,
    idempotent_notice="Idempotent so long as `restarted in {False, None}`, `reloaded in {False, None}`, and `command=None`.",
)
def service(
    service: str | Sequence[str],
    running: bool | None = None,
    restarted: bool | None = None,
    reloaded: bool | None = None,
    enabled: bool | None = None,
    the_set: str = "current",
    enabled_rx: str = "active",
    disabled_rx: str = "usable",
    do_commit: bool | None = None,
    do_install: bool | None = None,
    repodir: str | None = None,
    livedir: str | None = None,
    reload_timeout: float | None = 10,
    command: str | None = None,
):
    """
    Manage the state of s6-supervise'd services.

    .. important::
        This operation is in alpha. Things may break if you use it. Additionally, there is no
        support for bundles at this time; manage them at your own risk.

    + service: name(s) of the service(s) to manage.
    + running: whether the service(s) should be under an `s6-supervise`.
    + restarted: whether the service(s) should be restarted.
    + reloaded: whether the service(s) should be reloaded.
    + enabled: whether the service should be given an `active` or `usable` prescription.
    + the_set: name of the set to use when managing enabled status, using the set named "current" by default.
    + enabled_rx: name of the prescription to assign to the service(s) when enabled, which could be either `"active"` or `"always"`.
    + disabled_rx: name of the prescription to assign to the service(s) when disabled, which could be either `"usable"` or `"masked"`.
    + do_commit: whether to compile a new service database after changing the enabled status of the service(s) in `the_set`. Default is not to commit.
    + do_install: whether to install the set to the livedir.
    + repodir: path to the repository to manage when `enabled` is specified. Uses the one configured for `s6-frontend` by default.
    + livedir: path to the live state to manage when any of `running`, `restarted`, `reloaded` are specified. Uses the one configured for `s6-frontend` by default.
    + reload_timeout: number of seconds to wait for a service to reload.
    + command: custom command to run after the auto-computed commands. This must be an s6 subcommand, e.g. `"system reboot"` gives the command `s6 system reboot`.

    This operation can manage multiple services at once.

    Note that this operation does not give as granular control over
    prescriptions as the `manage_set` operation does; all services speecified
    will be assigned the same prescription if `enabled` is set.
    """

    logger.warning("The `s6.service` operation is in alpha!")

    if enabled_rx not in {"active", "always"}:
        raise ValueError('enabled_rx must be either "active" or "always"')
    if disabled_rx not in {"usable", "masked"}:
        raise ValueError('disabled_rx must be either "usable" or "masked"')

    if isinstance(service, str):
        service = (service,)

    if (running, restarted, reloaded) != (None,) * 3:
        # dict[str, bool] whether each service given in the services arg are running.
        live_statuses = {srv: host.get_fact(S6LiveStatus, livedir=livedir)[srv] for srv in service}
        all_up = all(live_statuses.values())
        some_up = any(live_statuses.values())
        all_down_services = [srv for srv, stat in live_statuses.items() if not stat]
        all_up_services = [srv for srv, stat in live_statuses.items() if stat]

        if running is False:
            if some_up:
                yield _make_live_change_command("stop", all_up_services, livedir=livedir)
            else:
                host.noop(f"all specified services are already down: {', '.join(service)}")

        if running is True:
            if not all_up:
                yield _make_live_change_command("start", all_down_services, livedir=livedir)
            else:
                host.noop(f"all specified services are already up: {', '.join(service)}")

        if restarted:
            if some_up:
                yield _make_live_change_command("restart", all_up_services, livedir=livedir)
            else:
                host.noop(f"all specified services are down: {', '.join(service)}")

        if reloaded:
            if some_up:
                if livedir:
                    yield make_formatted_string_command(
                        f"s6-rc -l {{{len(all_up_services)}}} -t {reload_timeout} reload "
                        + _make_format_fields(len(all_up_services)),
                        *map(QuoteString, all_up_services),
                        livedir,
                    )
                else:
                    yield make_formatted_string_command(
                        f"s6 live reload -t {reload_timeout} "
                        + _make_format_fields(len(all_up_services)),
                        *map(QuoteString, all_up_services),
                    )
            else:
                host.noop(f"all specified services are down: {', '.join(service)}")

    if enabled is not None:
        if enabled is True:
            yield from manage_set._inner(
                the_set=the_set,
                prescriptions={srv: enabled_rx for srv in service},
                do_commit=bool(do_commit),
                do_install=bool(do_install),
                repodir=repodir,
            )

        if enabled is False:
            yield from manage_set._inner(
                the_set=the_set,
                prescriptions={srv: disabled_rx for srv in service},
                do_commit=bool(do_commit),
                do_install=bool(do_install),
                repodir=repodir,
            )

    if command:
        yield StringCommand("s6", *map(QuoteString, shlex.split(command)))
