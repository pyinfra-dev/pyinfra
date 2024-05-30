import re
import shlex

from pyinfra.api import FactBase

from .util.packaging import parse_packages

rpm_regex = r"^(\S+)\ (\S+)$"
rpm_query_format = "%{NAME} %{VERSION}-%{RELEASE}\\n"


class RpmPackages(FactBase):
    """
    Returns a dict of installed rpm packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    command = "rpm --queryformat {0} -qa".format(shlex.quote(rpm_query_format))
    requires_command = "rpm"

    default = dict

    def process(self, output):
        return parse_packages(rpm_regex, output)


class RpmPackage(FactBase):
    """
    Returns information on a .rpm file:

    .. code:: python

        {
            "name": "my_package",
            "version": "1.0.0",
        }
    """

    requires_command = "rpm"

    def command(self, package):
        return (
            "rpm --queryformat {0} -q {1} || "
            "! test -e {1} || "
            "rpm --queryformat {0} -qp {1} 2> /dev/null"
        ).format(shlex.quote(rpm_query_format), shlex.quote(package))

    def process(self, output):
        for line in output:
            matches = re.match(rpm_regex, line)
            if matches:
                return {
                    "name": matches.group(1),
                    "version": matches.group(2),
                }


class RpmPackageProvides(FactBase):
    """
    Returns a list of packages that provide the specified capability (command, file, etc).
    """

    default = list

    requires_command = "repoquery"

    @staticmethod
    def command(package):
        # Accept failure here (|| true) for invalid/unknown packages
        return "repoquery --queryformat {0} --whatprovides {1} || true".format(
            shlex.quote(rpm_query_format),
            shlex.quote(package),
        )

    @staticmethod
    def process(output):
        packages = []

        for line in output:
            matches = re.match(rpm_regex, line)
            if matches:
                packages.append(list(matches.groups()))

        return packages
