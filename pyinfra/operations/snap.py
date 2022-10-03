"""
Manage snap packages. See https://snapcraft.io/
"""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.snap import SnapPackage, SnapPackages


@operation
def package(
    package,
    channel="latest/stable",
    present=True,
):
    """
    Install/remove a snap package

    + package: package name
    + channel: tracking channel
    + present: whether the package should be installed

    **Examples:**

    .. code:: python

        # Install vlc snap
        snap.package(
            name="Install vlc",
            package="vlc",
        )

        # Remove vlc
        snap.package(
            name="Remove vlc",
            package="vlc",
            present=False,
        )

        # Install LXD using "4.0/stable" channel
        snap.package(
            name="Install LXD 4.0/stable",
            package="lxd",
            channel="4.0/stable",
        )
    """
    snap_packages = host.get_fact(SnapPackages)

    # it's installed
    if package in snap_packages:
        # we want the package
        if present:
            pkg_info = host.get_fact(SnapPackage, package=package)

            # the channel is different
            if pkg_info and "channel" in pkg_info and channel != pkg_info["channel"]:
                yield " ".join(["snap", "refresh", package, f"--channel={channel}"])
                pkg_info["channel"] = channel

        else:
            # we don't want it
            yield " ".join(["snap", "remove", package])
            snap_packages.remove(package)

    # it's not installed
    if package not in snap_packages:
        # we want it
        if present:
            yield " ".join(["snap", "install", package, f"--channel={channel}"])
            snap_packages.append(package)

        # we don't want it
        else:
            host.noop(f"snap package {package} is not installed")
