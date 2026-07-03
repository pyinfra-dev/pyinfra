from pyinfra.api import FactBase, QuoteString
from pyinfra.api.command import make_formatted_string_command


class S6RepositoryList(FactBase[list[str]]):
    """Returns the name of every set in a repository."""

    def check_preconditions(self, state, host):
        from pyinfra.facts.files import File

        # TODO allow passing S6_FRONTEND_CONF envvar
        if not host.get_fact(File("/etc/s6/frontend.conf")):
            return "couldn't read /etc/s6/frontend.conf or it doesn't exist"

    def requires_command(self, repository=None):
        # "s6" only sees the repository configured in /etc/s6-frontend.conf
        if repository:
            return "s6-rc-repo-list"

        return "s6"

    def command(self, repository=None):
        """
        + repository: path of the repository to inspect, default the one configured in `/etc/s6-frontend.conf`.
        """
        if repository:
            return make_formatted_string_command("s6-rc-repo-list -r {0}", QuoteString(repository))

        return "s6 repository list"

    def process(self, output):
        # "s6" command doesn't list the set named "current", while s6-rc-repo-list does. this
        # try-except normalizes the output.
        try:
            del output[output.index("current")]
        except ValueError:
            pass

        return output


class S6SetStatus(FactBase[dict[str, str]]):
    """Returns a dict of name -> rx (prescription) for each service in a given set.

    If the set does not exist, nothing is returned.

    > [!IMPORTANT]
    > The fact only returns `None` when the set doesn't exist if `3` is in the `_success_exit_codes`
    > parameter for the fact. It will throw an exception otherwise due to a limitation in pyinfra.

    """

    def check_preconditions(self, state, host):
        from pyinfra.facts.files import File

        # TODO allow passing S6_FRONTEND_CONF envvar
        if not host.get_fact(File("/etc/s6/frontend.conf")):
            return "couldn't read /etc/s6/frontend.conf or it doesn't exist"

    def requires_command(self, set="current", repository=None):
        if repository or set != "current":
            return "s6-rc-set-status"

        return "s6"

    def command(self, set="current", repository=None):
        """
        + set: the set to inspect.
        + repository: path of the repository to inspect, default `None` which resolves the following way: If `set` is unspecified, the repository in `/etc/s6-frontend.conf` will be used. If `set` is specified, the compiled-in default `/var/lib/s6-rc/repository` will be used.
        """
        if set != "current":
            if repository:
                return make_formatted_string_command(
                        "s6-rc-set-status -r {0} {1}; echo EXIT CODE: $?", QuoteString(repository), QuoteString(set)
                )

            return make_formatted_string_command("s6-rc-set-status {0}; echo EXIT CODE: $?", QuoteString(set))

        if repository:
            return make_formatted_string_command(
                    "s6-rc-set-status -r {0} current; echo EXIT CODE: $?", QuoteString(repository)
            )

        # TODO consider case where util-linux triggers column pretty printing
        return "s6 set status; echo EXIT CODE: $?"

    def process(self, output):
        # exit code 3: nonexistent set
        # NOTE: will have to always specify 3 as success exit code when using this fact
        if output[-1] == "EXIT CODE: 3":
            return

        return {
                triplet[0]: triplet[-1] for triplet in map(lambda line: line.partition("/"), output[:-1])
        }


class S6LiveStatus(FactBase[dict[str, bool]]):
    """
    Returns a dict of name -> status for each service in the live state.

    True when the service is "running", meaning the service is managed by an `s6-supervise`s, False
    otherwise.
    """

    # could also rewrite this using the "s6 live status" command
    def requires_command(self):
        return "s6"

    def check_preconditions(self, state, host):
        from pyinfra.facts.files import File

        # TODO allow passing S6_FRONTEND_CONF envvar
        if not host.get_fact(File("/etc/s6/frontend.conf")):
            return "couldn't read /etc/s6/frontend.conf or it doesn't exist"

    def command(self):
        return "s6 live status"

    def process(self, output):
        return {
            triple[0]: True if triple[2] == "up" else False
            for triple in map(lambda line: line.partition("/"), output)
        }
