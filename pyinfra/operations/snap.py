"""
Manage snap packages. See https://snapcraft.io/
"""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.snap import SnapPackage, SnapPackages


@operation
def package(
    packages=None,
    channel="latest/stable",
    classic=False,
    present=True,
):
    """
    Install/remove a snap package

    + packages: List of packages
    + channel: tracking channel
    + classic: Use classic confinement
    + present: whether the package should be installed

    ``classic``:
        Allows access to your system’s resources in much the same way traditional
        packages do. This option corresponds to the ``--classic`` argument.

    **Examples:**

    .. code:: python

        # Install vlc snap
        snap.package(
            name="Install vlc",
            packages="vlc",
        )

        # Install multiple snaps
        snap.package(
            name="Install vlc and hello-world",
            packages=["vlc", "hello-world"],
        )

        # Remove vlc
        snap.package(
            name="Remove vlc",
            packages="vlc",
            present=False,
        )

        # Install LXD using "4.0/stable" channel
        snap.package(
            name="Install LXD 4.0/stable",
            packages=["lxd"],
            channel="4.0/stable",
        )

        # Install neovim with classic confinement
        snap.package(
            name="Install Neovim",
            packages=["nvim"],
            classic=True,
        )
    """

    if packages is None:
        return

    if isinstance(packages, str):
        packages = [packages]

    snap_packages = host.get_fact(SnapPackages)

    install_packages = []
    remove_packages = []
    refresh_packages = []

    for package in packages:
        # it's installed
        if package in snap_packages:
            # we want the package
            if present:
                pkg_info = host.get_fact(SnapPackage, package=package)

                # the channel is different
                if pkg_info and "channel" in pkg_info and channel != pkg_info["channel"]:
                    refresh_packages.append(package)
                    pkg_info["channel"] = channel

            else:
                # we don't want it
                remove_packages.append(package)
                snap_packages.remove(package)

        # it's not installed
        if package not in snap_packages:
            # we want it
            if present:
                install_packages.append(package)
                snap_packages.append(package)

            # we don't want it
            else:
                host.noop(f"snap package {package} is not installed")

    install_cmd = ["snap", "install"]
    if classic:
        install_cmd.append("--classic")
    if install_packages:
        yield " ".join(install_cmd + install_packages + [f"--channel={channel}"])

    if remove_packages:
        yield " ".join(["snap", "remove"] + remove_packages)

    if refresh_packages:
        yield " ".join(["snap", "refresh"] + refresh_packages + [f"--channel={channel}"])
