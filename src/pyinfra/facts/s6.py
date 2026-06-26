from pyinfra.api import FactBase


# all sets in the repository
class S6RCSets(FactBase[list[str]]):
    """Returns the name of every set in a repository."""

    def requires_command(self, respository=None):
        return "s6-rc-repo-list"

    def command(self, repository=None):
        if repository:
            return f"s6-rc-repo-list -r {repository}"
        else:
            return "s6-rc-repo-list"

    def process(self, output):
        return output


class S6RCEnabled(FactBase[dict[str, str]]):
    """Returns a dict of name -> rx (prescription) for each service in a given set."""

    def requires_command(self, set, repository=None):
        return "s6-rc-set-status"

    def command(self, set, repository=None):
        if repository:
            return f"s6-rc-set-status -r {repository} {set}"
        else:
            return f"s6-rc-set-status {set}"

    def process(self, output):
        return {triplet[0]: triplet[-1] for triplet in map(lambda line: line.partition("/"), output)}


class S6RCStatus(FactBase[dict[str, bool]]):
    """
    Returns a dict of name -> status for each service in the live state.

    True means s6 is trying to keep the service up; False means the service is not managed by s6.
    """

    # default = dict

    def requires_command(self):
        return "s6-rc"

    def check_preconditions(self):
        pass

    def command(self):
        return r"{ s6-rc -a list && echo -e 'GROUP SEPARATOR' && s6-rc -da list ; } || exit 1"

    def process(self, output):
        status = {}

        gs_index = output.index("GROUP SEPARATOR")
        enabled_services = output[:gs_index]
        disabled_services = output[gs_index + 1 :]

        status.update([(srv, True) for srv in enabled_services])
        status.update([(srv, False) for srv in disabled_services])

        return status
