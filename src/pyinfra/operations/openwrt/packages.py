"""
Manage packages on OpenWrt using ``apk` or `opkg`` depending on the release of OpenWrt.
    + `packages` -  install and remove packages
    + `update` - update local copy of package information

See https://openwrt.org/docs/guide-user/additional-software/apk and
    https://openwrt.org/docs/guide-user/additional-software/opkg

TBD - OpenWrt recommends against upgrading all packages  thus there is no `opkg.upgrade` function

  .. note: As of [Release 25.12](https://openwrt.org/releases/25.12/notes-25.12.0#switch_package_manager_from_opkg_to_apk)
OpenWrt uses [apk](../operations/apk.md)

note: this does _not_ show up in the online documentation; the file header in __init__.py does.
"""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.openwrt import OpenWrtFeature, OpenWrtHasFeature
from pyinfra.operations import apk

from . import opkg


@operation(is_idempotent=False)
def update():
    """
    Update the local package information.
    See [apk](../operations/apk.md) and [opkg](../operations/openwrt.md) for more details.

        **Examples:**

    .. code:: python

        from pyinfra.operations import openwrt

        # Ensure local package information is up to date
        openwrt.update(name="Update the local package information")

    """
    if host.get_fact(OpenWrtHasFeature, OpenWrtFeature.USES_APK):
        yield from apk.update._inner()  # noqa: SLF001
    else:
        yield from opkg.update._inner()  # noqa: SLF001


@operation()
def packages(
    packages: str | list[str] | None = None,
    present: bool = True,
    latest: bool = False,
    update: bool = False,
):
    """
    Add/remove/update packages using ``apk`` or ``opkg``  depending on the OpenWrt release.

    + packages: package or list of packages to that must/must not be present (default ``True``).
    + present: whether the package(s) should be installed or removed (default ``True``).
    + latest: whether to attempt to upgrade the specified package(s) (default ``False``).
    + update: run ``apk|opkg update`` before installing packages (default ``False``).

    See [apk](../operations/apk.md) and [opkg](../operations/openwrt.md) for more details.

    **Examples:**

    .. code:: python

        from pyinfra.operations import openwrt
        # Ensure packages are installed (will not force package upgrade)
        openwrt.packages(['asterisk', 'vim'], name="Install Asterisk and Vim")

        # Install the latest versions of packages
        openwrt.packages(
            'vim',
            latest=True,
            name="Ensure we have the latest version of Vim"
        )
    """
    packages = [packages] if isinstance(packages, str) else (packages or [])
    if (len(packages) < 1) or any((len(p) < 1) or (p is None) for p in packages):
        host.noop("empty package list provided to openwrt.packages")
        return

    if host.get_fact(OpenWrtHasFeature, feature=OpenWrtFeature.USES_APK):
        yield from apk.packages._inner(  # noqa: SLF001
            packages=packages, latest=latest, update=update, present=present
        )
    else:
        yield from opkg.packages._inner(  # noqa: SLF001
            packages=packages, latest=latest, update=update, present=present
        )
