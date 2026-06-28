"""
Manage flatpak packages. See https://www.flatpak.org/
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.facts.flatpak import FlatpakPackages


@operation()
def packages(
    packages: str | list[str] | None = None,
    remote: str | None = None,
    present=True,
):
    """
    Install/remove a flatpak package

    + packages: List of packages
    + remote: Source to install the application or runtime from
    + present: whether the package should be installed

    **Examples:**

    .. code:: python

        from pyinfra.operations import flatpak
        # Install vlc flatpak
        flatpak.package(
            name="Install vlc",
            packages="org.videolan.VLC",
        )

        # Install vlc flatpak from flathub
        flatpak.package(
            name="Install vlc",
            packages="org.videolan.VLC",
            remote="flathub",
        )

        # Install multiple flatpaks
        flatpak.package(
            name="Install vlc and kodi",
            packages=["org.videolan.VLC", "tv.kodi.Kodi"],
        )

        # Remove vlc
        flatpak.package(
            name="Remove vlc",
            packages="org.videolan.VLC",
            present=False,
        )
    """

    if packages is None:
        return

    if isinstance(packages, str):
        packages = [packages]

    flatpak_packages = host.get_fact(FlatpakPackages)

    install_packages = []
    remove_packages = []

    if remote is not None:
        remote = remote.strip()

    for package in packages:
        # it's installed
        if package in flatpak_packages:
            if not present:
                # we don't want it
                remove_packages.append(package)

        # it's not installed
        if package not in flatpak_packages:
            # we want it
            if present:
                install_packages.append(package)

            # we don't want it
            else:
                host.noop(f"flatpak package {package} is not installed")

    if install_packages:
        command: list[str | QuoteString] = ["flatpak install --noninteractive"]
        if remote:
            command.append(QuoteString(remote))
        command += [QuoteString(package) for package in install_packages]
        yield StringCommand(*command)

    if remove_packages:
        yield StringCommand(
            "flatpak uninstall --noninteractive",
            *[QuoteString(package) for package in remove_packages],
        )
