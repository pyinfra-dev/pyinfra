from typing_extensions import override

from pyinfra.api import FactBase, QuoteString
from pyinfra.api.command import make_formatted_string_command, StringCommand


class S6RepositoryList(FactBase[list[str]]):
    """Returns the name of every set in a repository, including the set named "current"."""

    @override
    def requires_command(self, repodir=None):
        if repodir is None:
            return "s6"
        return "s6-rc-repo-list"
        # and envfile, but that comes bundled in execline dependency of s6

    @override
    def command(self, repodir=None):
        """
        + repodir: path of the repository to inspect. If `None`, the one configured for s6-frontend will be used.
        """
        if repodir:
            return make_formatted_string_command("s6-rc-repo-list -r {0}", QuoteString(repodir))

        return StringCommand("s6 repo list")

        # if no repository passed, try to get its location from the s6-frontend configuration file
        # return StringCommand(
        #    '[ ! -z "$S6_CONF" ] || S6_CONF=/etc/s6.conf && envfile "$S6_CONF" sh -c \'s6-rc-repo-list -r "$repodir"\'; echo EXIT CODE: $?'
        # )

    @override
    def process(self, output):
        if "No such file or directory" not in output[0]:
            return output


class S6SetStatus(FactBase[dict[str, str]]):
    """Returns a dict of name -> rx (prescription) for each service in a given set."""

    @override
    def requires_command(self, the_set="current", repodir=None):
        if repodir is None:
            return "s6"
        return "s6-rc-set-status"
        # and sh

    @override
    def command(self, the_set="current", repodir=None):
        """
        + the_set: the set to inspect.
        + repository: path of the repository to inspect, default `None`, which means to use the one configured for s6-frontend.
        """
        if repodir:
            return make_formatted_string_command(
                "s6-rc-set-status -r {0} {1}",
                QuoteString(repodir),
                QuoteString(the_set),
            )

        # s6-frontend opportunistically pretty-prints set status output. It should detect when the
        # terminal does not have a user behind it and fall back to the "service/rx" per line output,
        # but if there are output processing bugs, this behavior could be the cause.
        return make_formatted_string_command(
            "s6 set status -s {0}", QuoteString(the_set)
        )
        # extra escaping needed for make_formatted_string_command, but not in StringCommand
        # return make_formatted_string_command(
        #    '[ ! -z \\"$S6_CONF\\" ] || S6_CONF=/etc/s6.conf && envfile \\"$S6_CONF\\" sh -c \\\'s6-rc-set-status -r \\"$repodir\\" {0}\\\'; echo EXIT CODE: $?',
        #    QuoteString(the_set),
        # )

    @override
    def process(self, output):
        # repository does not exist
        if "No such file or directory" in output[0]:
            return
        # repository exists, but set does not
        if "does not exist in repository" in output[0]:
            return

        return {
            triplet[0]: triplet[-1]
            for triplet in map(lambda line: line.partition("/"), output)
        }

class S6LiveStatus(FactBase[dict[str, bool]]):
    """Returns a dict of name -> status for each service in the live state.

    True when the service is "running", meaning the service is managed by an `s6-supervise`s, False
    otherwise.
    """

    @override
    def requires_command(self, livedir=None):
        """
        + livedir: the directory of the live state. If `None`, it will use the one configured for s6-frontend.
        """
        if livedir is None:
            return "s6"
        return "s6-rc"

    # @override
    # def check_preconditions(self, state, host):
    #    if not host.run_shell_command('[ ! -z "$S6_CONF" ] || [ -f /etc/s6.conf ]')[0]:
    #        return "couldn't find s6-frontend configuration"

    @override
    def command(self, livedir=None):
        if livedir:
            return make_formatted_string_command("s6-rc -l {0} -c list", QuoteString(livedir))
        return "s6 live status"

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
