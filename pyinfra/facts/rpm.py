from __future__ import unicode_literals

import re

from pyinfra.api import FactBase

from .util.packaging import parse_packages

rpm_regex = r'^(\S+)\ (\S+)$'
rpm_query_format = '%{NAME} %{VERSION}-%{RELEASE}\\n'


class RPMPackages(FactBase):
    '''
    Returns a dict of installed rpm packages:

    .. code:: python

        'package_name': ['version'],
        ...
    '''

    command = 'rpm --queryformat "{0}" -qa'.format(rpm_query_format)
    default = dict
    use_default_on_error = True

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
            'version': '1.0.0'
        }
    '''

    use_default_on_error = True

    def command(self, name):
        return ('rpm --queryformat "{0}" -qp {1} 2> /dev/null || '
                'rpm --queryformat "{0}" -q {1}'.format(rpm_query_format, name))

    def process(self, output):
        for line in output:
            matches = re.match(rpm_regex, line)
            if matches:
                return {
                    'name': matches.group(1),
                    'version': matches.group(2),
                }
