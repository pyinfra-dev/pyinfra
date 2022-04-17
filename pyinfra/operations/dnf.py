"""
Manage dnf packages and repositories. Note that dnf package names are case-sensitive.
"""

from pyinfra import host, state
from pyinfra.api import operation
from pyinfra.facts.rpm import RpmPackageProvides, RpmPackages

from . import files
from .util.packaging import ensure_packages, ensure_rpm, ensure_yum_repo


@operation(is_idempotent=False)
def key(src):
    """
    Add dnf gpg keys with ``rpm``.

    + key: filename or URL

    Note:
        always returns one command, not idempotent

    **Example:**

    .. code:: python

        linux_id = host.get_fact(LinuxDistribution)["release_meta"].get("ID")
        dnf.key(
            name="Add the Docker CentOS gpg key",
            src=f"https://download.docker.com/linux/{linux_id}/gpg",
        )

    """

    yield "rpm --import {0}".format(src)


@operation
def repo(
    src,
    present=True,
    baseurl=None,
    description=None,
    enabled=True,
    gpgcheck=True,
    gpgkey=None,
):
    # NOTE: if updating this docstring also update `yum.repo`
    """
    Add/remove/update dnf repositories.

    + name: URL or name for the ``.repo``   file
    + present: whether the ``.repo`` file should be present
    + baseurl: the baseurl of the repo (if ``name`` is not a URL)
    + description: optional verbose description
    + enabled: whether this repo is enabled
    + gpgcheck: whether set ``gpgcheck=1``
    + gpgkey: the URL to the gpg key for this repo

    ``Baseurl``/``description``/``gpgcheck``/``gpgkey``:
        These are only valid when ``name`` is a filename (ie not a URL). This is
        for manual construction of repository files. Use a URL to download and
        install remote repository files.

    **Examples:**

    .. code:: python

        # Download a repository file
        dnf.rpm(
            name="Install Docker-CE repo via URL",
            src="https://download.docker.com/linux/centos/docker-ce.repo",
        )

        # Create the repository file from baseurl/etc
        dnf.repo(
            name="Add the Docker CentOS repo",
            src="DockerCE",
            baseurl="https://download.docker.com/linux/centos/7/$basearch/stable",
        )
    """

    yield from ensure_yum_repo(
        state,
        host,
        files,
        src,
        baseurl,
        present,
        description,
        enabled,
        gpgcheck,
        gpgkey,
    )


@operation
def rpm(src, present=True):
    # NOTE: if updating this docstring also update `yum.rpm`
    """
    Add/remove ``.rpm`` file packages.

    + src: filename or URL of the ``.rpm`` package
    + present: whether ore not the package should exist on the system

    URL sources with ``present=False``:
        If the ``.rpm`` file isn't downloaded, pyinfra can't remove any existing
        package as the file won't exist until mid-deploy.

    **Example:**

    .. code:: python

        major_centos_version = host.get_fact(LinuxDistribution)["major"]
        dnf.rpm(
           name="Install EPEL rpm to enable EPEL repo",
           src=f"https://dl.fedoraproject.org/pub/epel/epel-release-latest-{major_centos_version}.noarch.rpm",
        )
    """

    yield from ensure_rpm(state, host, files, src, present, "dnf")


@operation(is_idempotent=False)
def update():
    """
    Updates all dnf packages.
    """

    yield "dnf update -y"


_update = update  # noqa: E305 (for use below where update is a kwarg)


@operation
def packages(
    packages=None,
    present=True,
    latest=False,
    update=False,
    clean=False,
    nobest=False,
    extra_install_args=None,
    extra_uninstall_args=None,
):
    """
    Install/remove/update dnf packages & updates.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run ``dnf update`` before installing packages
    + clean: run ``dnf clean`` before installing packages
    + nobest: add the no best option to install
    + extra_install_args: additional arguments to the dnf install command
    + extra_uninstall_args: additional arguments to the dnf uninstall command

    Versions:
        Package versions can be pinned as follows: ``<pkg>=<version>``

    **Examples:**

    .. code:: python

        # Update package list and install packages
        dnf.packages(
            name='Install Vim and Vim enhanced',
            packages=["vim-enhanced", "vim"],
            update=True,
        )

        # Install the latest versions of packages (always check)
        dnf.packages(
            name="Install latest Vim",
            packages=["vim"],
            latest=True,
        )
    """

    if clean:
        yield "dnf clean all"

    if update:
        yield from _update()

    install_command = ["dnf", "install", "-y"]

    if nobest:
        install_command.append("--nobest")

    if extra_install_args:
        install_command.append(extra_install_args)

    uninstall_command = ["dnf", "remove", "-y"]

    if extra_uninstall_args:
        uninstall_command.append(extra_uninstall_args)

    yield from ensure_packages(
        host,
        packages,
        host.get_fact(RpmPackages),
        present,
        install_command=" ".join(install_command),
        uninstall_command=" ".join(uninstall_command),
        upgrade_command="dnf update -y",
        version_join="=",
        latest=latest,
        expand_package_fact=lambda package: host.get_fact(
            RpmPackageProvides,
            name=package,
        ),
    )
