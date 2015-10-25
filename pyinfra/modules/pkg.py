# pyinfra
# File: pyinfra/modules/pkg.py
# Desc: manage BSD packages with pkg_*

'''
Manage BSD packages and repositories. Note that BSD package names are case-sensitive.
'''

from pyinfra.api import operation, OperationException


@operation
def packages(state, host, packages=None, present=True):
    if packages is None:
        packages = []

    commands = []

    current_packages = host.pkg_packages or {}

    if current_packages is None:
        raise OperationException('pkg_* are not installed')

    if present is True:
        # We have to set the pkg_path manually as the env var (seemingly, OpenBSD 5.6) isn't created
        # for non-tty requests such as pyinfra's
        pkg_path = 'http://ftp.{http}.org/pub/{os}/{version}/packages/{arch}/'.format(
            http=host.os.lower(),
            os=host.os,
            version=host.os_version,
            arch=host.arch
        )

        diff_packages = [
            package for package in packages
            if package not in current_packages
        ]

        if diff_packages:
            commands.append('PKG_PATH={0} pkg_add {1}'.format(pkg_path, ' '.join(diff_packages)))

    else:
        diff_packages = [
            package for package in packages
            if package in current_packages
        ]

        if diff_packages:
            commands.append('pkg_delete {0}'.format(' '.join(diff_packages)))

    return commands
