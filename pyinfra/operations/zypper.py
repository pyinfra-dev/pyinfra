from pyinfra import host, state
from pyinfra.api import operation
from pyinfra.facts.rpm import RpmPackages

from . import files
from .util.packaging import ensure_packages, ensure_rpm, ensure_yum_repo
from .yum import key as yum_key

key = yum_key


@operation
def repo(
    src,
    baseurl=None,
    present=True,
    description=None,
    enabled=True,
    gpgcheck=True,
    gpgkey=None,
    type="rpm-md",
):
    """
    Add/remove/update zypper repositories.

    + src: URL or name for the ``.repo``   file
    + baseurl: the baseurl of the repo (if ``name`` is not a URL)
    + present: whether the ``.repo`` file should be present
    + description: optional verbose description
    + enabled: whether this repo is enabled
    + gpgcheck: whether set ``gpgcheck=1``
    + gpgkey: the URL to the gpg key for this repo
    + type: the type field this repo (defaults to ``rpm-md``)

    ``Baseurl``/``description``/``gpgcheck``/``gpgkey``:
        These are only valid when ``name`` is a filename (ie not a URL). This is
        for manual construction of repository files. Use a URL to download and
        install remote repository files.

    **Examples:**

    .. code:: python

        # Download a repository file
        zypper.repo(
            name="Install container virtualization repo via URL",
            src="https://download.opensuse.org/repositories/Virtualization:containers/openSUSE_Tumbleweed/Virtualization:containers.repo",
        )

        # Create the repository file from baseurl/etc
        zypper.repo(
            name="Install container virtualization repo",
            src=="Virtualization:containers (openSUSE_Tumbleweed)",
            baseurl="https://download.opensuse.org/repositories/Virtualization:/containers/openSUSE_Tumbleweed/",
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
        type_=type,
        repo_directory="/etc/zypp/repos.d/",
    )


@operation
def rpm(src, present=True):
    # NOTE: if updating this docstring also update `dnf.rpm`
    """
    Add/remove ``.rpm`` file packages.

    + src: filename or URL of the ``.rpm`` package
    + present: whether ore not the package should exist on the system

    URL sources with ``present=False``:
        If the ``.rpm`` file isn't downloaded, pyinfra can't remove any existing
        package as the file won't exist until mid-deploy.

    **Example:**

    .. code:: python

        zypper.rpm(
           name="Install task from rpm",
           src="https://github.com/go-task/task/releases/download/v2.8.1/task_linux_amd64.rpm",
        )
    """

    yield from ensure_rpm(state, host, files, src, present, "zypper --non-interactive")


@operation(is_idempotent=False)
def update():
    """
    Updates all zypper packages.
    """

    yield "zypper update -y"


_update = update  # noqa: E305 (for use below where update is a kwarg)


@operation
def packages(
    packages=None,
    present=True,
    latest=False,
    update=False,
    clean=False,
    extra_global_install_args=None,
    extra_install_args=None,
    extra_global_uninstall_args=None,
    extra_uninstall_args=None,
):
    """
    Install/remove/update zypper packages & updates.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run ``zypper update`` before installing packages
    + clean: run ``zypper clean --all`` before installing packages
    + extra_global_install_args: additional global arguments to the zypper install command
    + extra_install_args: additional arguments to the zypper install command
    + extra_global_uninstall_args: additional global arguments to the zypper uninstall command
    + extra_uninstall_args: additional arguments to the zypper uninstall command

    Versions:
        Package versions can be pinned like zypper: ``<pkg>=<version>``

    **Examples:**

    .. code:: python

        # Update package list and install packages
        zypper.packages(
            name="Install Vim and Vim enhanced",
            packages=["vim-enhanced", "vim"],
            update=True,
        )

        # Install the latest versions of packages (always check)
        zypper.packages(
            name="Install latest Vim",
            packages=["vim"],
            latest=True,
        )
    """

    if clean:
        yield "zypper clean --all"

    if update:
        yield from _update()

    install_command = ["zypper", "--non-interactive", "install", "-y"]

    if extra_install_args:
        install_command.append(extra_install_args)

    if extra_global_install_args:
        install_command.insert(1, extra_global_install_args)

    uninstall_command = ["zypper", "--non-interactive", "remove", "-y"]

    if extra_uninstall_args:
        uninstall_command.append(extra_uninstall_args)

    if extra_global_uninstall_args:
        uninstall_command.insert(1, extra_global_uninstall_args)

    upgrade_command = "zypper update -y"

    yield from ensure_packages(
        host,
        packages,
        host.get_fact(RpmPackages),
        present,
        install_command=" ".join(install_command),
        uninstall_command=" ".join(uninstall_command),
        upgrade_command=upgrade_command,
        version_join="=",
        latest=latest,
    )
