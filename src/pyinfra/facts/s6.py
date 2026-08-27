from typing_extensions import override

from pyinfra.api import FactBase, QuoteString
from pyinfra.api.command import make_formatted_string_command, StringCommand
from pyinfra.facts.server import Command
from pyinfra.facts.files import File


class S6RepositoryList(FactBase[list[str]]):
    """Returns the name of every set in a repository, including the set named "current"."""

    @override
    def requires_command(self, repository=None):
        return "s6-rc-repo-list"
        # and envfile, but that comes bundled in execline dependency of s6

    @override
    def command(self, repository=None):
        """
        + repository: path of the repository to inspect. If `None`, the compiled-in default will be used, most likely `/var/lib/s6/repository`.
        """
        if repository:
            return make_formatted_string_command("s6-rc-repo-list -r {0}", QuoteString(repository))

        return StringCommand("s6-rc-repo-list")

        # if no repository passed, try to get its location from the s6-frontend configuration file
        # return StringCommand(
        #    '[ ! -z "$S6_CONF" ] || S6_CONF=/etc/s6.conf && envfile "$S6_CONF" sh -c \'s6-rc-repo-list -r "$repodir"\'; echo EXIT CODE: $?'
        # )

    @override
    def process(self, output):
        return output


class S6SetStatus(FactBase[dict[str, str]]):
    """Returns a dict of name -> rx (prescription) for each service in a given set.

    If the set does not exist, nothing is returned.

    > [!IMPORTANT]
    > The fact only returns `None` when the set doesn't exist if `3` is in the `_success_exit_codes`
    > parameter for the fact. It will throw an exception otherwise due to a limitation in pyinfra.

    """

    @override
    def requires_command(self, the_set="current", repository=None):
        return "s6-rc-set-status"
        # and sh

    @override
    def command(self, the_set="current", repository=None):
        """
        + the_set: the set to inspect.
        + repository: path of the repository to inspect, default `None`, which means to use the compiled-in default repository most likely `/var/lib/s6/repository`.
        """
        if repository:
            return make_formatted_string_command(
                "s6-rc-set-status -r {0} {1}; echo EXIT CODE: $?",
                QuoteString(repository),
                QuoteString(the_set),
            )

        return make_formatted_string_command(
            "s6-rc-set-status {0}; echo EXIT CODE: $?", QuoteString(the_set)
        )
        # extra escaping needed for make_formatted_string_command, but not in StringCommand
        # return make_formatted_string_command(
        #    '[ ! -z \\"$S6_CONF\\" ] || S6_CONF=/etc/s6.conf && envfile \\"$S6_CONF\\" sh -c \\\'s6-rc-set-status -r \\"$repodir\\" {0}\\\'; echo EXIT CODE: $?',
        #    QuoteString(the_set),
        # )

    @override
    def process(self, output):
        # exit code 3: nonexistent set
        # NOTE: will have to always specify 3 as success exit code when using this fact
        if output[-1] == "EXIT CODE: 3":
            return

        return {
            triplet[0]: triplet[-1]
            for triplet in map(lambda line: line.partition("/"), output[:-1])
        }


class S6LiveStatus(FactBase[dict[str, bool]]):
    """Returns a dict of name -> status for each service in the live state.

    True when the service is "running", meaning the service is managed by an `s6-supervise`s, False
    otherwise.
    """

    @override
    def requires_command(self):
        return "s6-rc"

    # @override
    # def check_preconditions(self, state, host):
    #    if not host.run_shell_command('[ ! -z "$S6_CONF" ] || [ -f /etc/s6.conf ]')[0]:
    #        return "couldn't find s6-frontend configuration"

    @override
    def command(self):
        return "s6-rc -c list"

    @override
    def process(self, output):
        # example of an output line:
        #    seatd-srv/longrun//up/explicit
        # returns
        #    { "seatd-srv": True }
        return {
            statusline[0]: True if statusline[3] == "up" else False
            for statusline in map(lambda line: line.split("/"), output)
        }
