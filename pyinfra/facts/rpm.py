from __future__ import unicode_literals

import re

from pyinfra.api import FactBase

from .util.packaging import parse_packages

rpm_regex = r'^(\S+)\ (\S+)$'
rpm_query_format = '%{NAME} %{VERSION}-%{RELEASE}\\n'


class RpmPackages(FactBase):
    '''
    Returns a dict of installed rpm packages:

    .. code:: python

        {
            'package_name': ['version'],
        }
    '''

    command = 'rpm --queryformat "{0}" -qa'.format(rpm_query_format)
    requires_command = 'rpm'

    default = dict

    def process(self, output):
        return parse_packages(
            rpm_regex, output,
            # yum packages are case-sensitive
            lower=False,
        )


class RpmPackage(FactBase):
    '''
    Returns information on a .rpm file:

    .. code:: python

        {
            'name': 'my_package',
            'version': '1.0.0',
        }
    '''

    requires_command = 'rpm'

    def command(self, name):
        return (
            '! test -e {1} || '
            '(rpm --queryformat "{0}" -qp {1} 2> /dev/null || rpm --queryformat "{0}" -q {1})'
        ).format(rpm_query_format, name)

    def process(self, output):
        for line in output:
            matches = re.match(rpm_regex, line)
            if matches:
                return {
                    'name': matches.group(1),
                    'version': matches.group(2),
                }


class RpmPackageProvides(FactBase):
    '''
    Returns a list of packages that provide the specified capability (command, file, etc).
    '''

    default = list

    requires_command = 'repoquery'

    @staticmethod
    def command(name):
        # Accept failure here (|| true) for invalid/unknown packages
        return 'repoquery --queryformat "{0}" --whatprovides {1} || true'.format(
            rpm_query_format,
            name,
        )

    @staticmethod
    def process(output):
        packages = []

        for line in output:
            matches = re.match(rpm_regex, line)
            if matches:
                packages.append(list(matches.groups()))

        return packages
