from pyinfra.api import FactBase


class S6RepositoryList(FactBase[list[str]]):
    """Returns the name of every set in a repository."""

    def check_preconditions(self, state, host):
        from pyinfra.facts.files import File
        if not host.get_fact(File("/etc/s6/frontend.conf")):
            return "/etc/s6/frontend.conf doesn't exist"

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
            return f"s6-rc-repo-list -r {repository}"

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
    """Returns a dict of name -> rx (prescription) for each service in a given set."""

    def check_preconditions(self, state, host):
        from pyinfra.facts.files import File
        if not host.get_fact(File("/etc/s6/frontend.conf")):
            return "/etc/s6/frontend.conf doesn't exist"

    def requires_command(self, repository=None, set=None):
        if repository or set:
            return "s6-rc-set-status"

        return "s6"

    def command(self, set=None, repository=None):
        """
        + set: the set to inspect, default `None` which resolves to the current working set "current".
        + repository: path of the repository to inspect, default `None` which resolves the following way: If `set` is unspecified, the repository in `/etc/s6-frontend.conf` will be used. If `set` is specified, the compiled-in default `/var/lib/s6-rc/repository` will be used.
        """
        if set:
            if repository:
                return f"s6-rc-set-status -r {repository} {set}"

            return f"s6-rc-set-status {set}"

        if repository:
            if set:
                return f"s6-rc-set-status -r {repository} {set}"

            return f"s6-rc-set-status -r {repository} current"

        return "s6 set status"

    def process(self, output):
        return {
            triplet[0]: triplet[-1] for triplet in map(lambda line: line.partition("/"), output)
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
        if not host.get_fact(File("/etc/s6/frontend.conf")):
            return "/etc/s6/frontend.conf doesn't exist"

    def command(self):
        return "s6 live status"

    def process(self, output):
        return {
            triple[0]: True if triple[2] == "up" else False
            for triple in map(lambda line: line.partition("/"), output)
        }
