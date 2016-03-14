# pyinfra
# File: pyinfra/modules/pkg.py
# Desc: manage BSD packages with pkg_*

'''
Manage BSD packages and repositories. Note that BSD package names are case-sensitive.
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def packages(state, host, packages=None, present=True):
    '''
    Manage pkg_* packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    '''

    pkg_path = ''

    if present is True:
        host_os = host.fact.os or ''

        # We have to set the pkg_path manually as the env var (seemingly, OpenBSD 5.6)
        # isn't created for non-tty requests such as pyinfra's
        pkg_path = 'http://ftp.{http}.org/pub/{os}/{version}/packages/{arch}/'.format(
            http=host_os.lower(),
            os=host_os,
            version=host.fact.os_version,
            arch=host.fact.arch
        )

    return ensure_packages(
        packages, host.fact.pkg_packages, present,
        install_command='PKG_PATH={0} pkg_add'.format(pkg_path),
        uninstall_command='pkg_delete'
    )
