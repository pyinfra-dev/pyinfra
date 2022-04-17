"""
Manage pip (python) packages. Compatible globally or inside
a virtualenv (virtual environment).
"""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.files import File
from pyinfra.facts.pip import PipPackages

from . import files
from .util.packaging import ensure_packages


@operation
def virtualenv(
    path,
    python=None,
    venv=False,
    site_packages=False,
    always_copy=False,
    present=True,
):
    """
    Add/remove Python virtualenvs.

    + python: python interpreter to use
    + venv: use standard venv module instead of virtualenv
    + site_packages: give access to the global site-packages
    + always_copy: always copy files rather than symlinking
    + present: whether the virtualenv should exist

    **Example:**

    .. code:: python

        pip.virtualenv(
            name="Create a virtualenv",
            path="/usr/local/bin/venv",
        )
    """

    # Check for *contents* of a virtualenv, ie don't accept an empty directory
    # as a valid virtualenv but ensure the activate script exists.
    activate_script_path = "{0}/bin/activate".format(path)

    if present is False:
        if host.get_fact(File, path=activate_script_path):
            yield from files.directory(path, present=False)
        else:
            host.noop("virtualenv {0} does not exist".format(path))

    if present:
        if not host.get_fact(File, path=activate_script_path):
            # Create missing virtualenv
            command = ["virtualenv"]

            if venv:
                command = [python or "python", "-m", "venv"]

            if python and not venv:
                command.append("-p {0}".format(python))

            if site_packages:
                command.append("--system-site-packages")

            if always_copy and not venv:
                command.append("--always-copy")
            elif always_copy and venv:
                command.append("--copies")

            command.append(path)

            yield " ".join(command)

            host.create_fact(
                File,
                kwargs={"path": activate_script_path},
                data={"user": None, "group": None},
            )
        else:
            host.noop("virtualenv {0} exists".format(path))


_virtualenv = virtualenv  # noqa


@operation
def venv(
    path,
    python=None,
    site_packages=False,
    always_copy=False,
    present=True,
):
    """
    Add/remove Python virtualenvs.

    + python: python interpreter to use
    + site_packages: give access to the global site-packages
    + always_copy: always copy files rather than symlinking
    + present: whether the virtualenv should exist

    **Example:**

    .. code:: python

        pip.venv(
            name="Create a virtualenv",
            path="/usr/local/bin/venv",
        )
    """

    yield from virtualenv(
        venv=True,
        path=path,
        python=python,
        site_packages=site_packages,
        always_copy=always_copy,
        present=present,
    )


@operation
def packages(
    packages=None,
    present=True,
    latest=False,
    requirements=None,
    pip="pip",
    virtualenv=None,
    virtualenv_kwargs=None,
    extra_install_args=None,
):
    """
    Install/remove/update pip packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + requirements: location of requirements file to install/uninstall
    + pip: name or path of the pip directory to use
    + virtualenv: root directory of virtualenv to work in
    + virtualenv_kwargs: dictionary of arguments to pass to ``pip.virtualenv``
    + extra_install_args: additional arguments to the pip install command

    Virtualenv:
        This will be created if it does not exist already. ``virtualenv_kwargs``
        will be passed to ``pip.virtualenv`` which can be used to control how
        the env is created.

    Versions:
        Package versions can be pinned like pip: ``<pkg>==<version>``.

    **Example:**

    .. code:: python

        pip.packages(
            name="Install pyinfra into a virtualenv",
            packages=["pyinfra"],
            virtualenv="/usr/local/bin/venv",
        )
    """

    virtualenv_kwargs = virtualenv_kwargs or {}

    # Ensure any virtualenv
    if virtualenv:
        yield from _virtualenv(virtualenv, **virtualenv_kwargs)

        # And update pip path
        virtualenv = virtualenv.rstrip("/")
        pip = "{0}/bin/{1}".format(virtualenv, pip)

    install_command = [pip, "install"]
    if extra_install_args:
        install_command.append(extra_install_args)
    install_command = " ".join(install_command)

    uninstall_command = " ".join([pip, "uninstall", "--yes"])

    # (un)Install requirements
    if requirements is not None:
        if present:
            yield "{0} -r {1}".format(install_command, requirements)
        else:
            yield "{0} -r {1}".format(uninstall_command, requirements)

    # Handle passed in packages
    if packages:
        current_packages = host.get_fact(PipPackages, pip=pip)

        yield from ensure_packages(
            host,
            packages,
            current_packages,
            present,
            install_command=install_command,
            uninstall_command=uninstall_command,
            upgrade_command="{0} --upgrade".format(install_command),
            version_join="==",
            latest=latest,
        )
