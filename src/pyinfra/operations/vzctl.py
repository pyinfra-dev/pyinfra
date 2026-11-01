"""
Manage OpenVZ containers with ``vzctl``.
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import OperationError, QuoteString, StringCommand, operation
from pyinfra.facts.vzctl import OpenvzContainers


@operation(is_idempotent=False)
def start(ctid: str, force=False):
    """
    Start OpenVZ containers.

    + ctid: CTID of the container to start
    + force: whether to force container start
    """

    command: list[str | QuoteString] = ["vzctl start", QuoteString(str(ctid))]

    if force:
        command.append("--force")

    yield StringCommand(*command)


@operation(is_idempotent=False)
def stop(ctid: str):
    """
    Stop OpenVZ containers.

    + ctid: CTID of the container to stop
    """

    yield StringCommand("vzctl stop", QuoteString(str(ctid)))


@operation(is_idempotent=False)
def restart(ctid: str, force=False):
    """
    Restart OpenVZ containers.

    + ctid: CTID of the container to restart
    + force: whether to force container start
    """

    yield from stop._inner(ctid=ctid)
    yield from start._inner(ctid=ctid, force=force)


@operation(is_idempotent=False)
def mount(ctid: str):
    """
    Mount OpenVZ container filesystems.

    + ctid: CTID of the container to mount
    """

    yield StringCommand("vzctl mount", QuoteString(str(ctid)))


@operation(is_idempotent=False)
def unmount(ctid: str):
    """
    Unmount OpenVZ container filesystems.

    + ctid: CTID of the container to unmount
    """

    yield StringCommand("vzctl umount", QuoteString(str(ctid)))


@operation(is_idempotent=False)
def delete(ctid: str):
    """
    Delete OpenVZ containers.

    + ctid: CTID of the container to delete
    """

    yield StringCommand("vzctl delete", QuoteString(str(ctid)))


@operation(is_idempotent=False)
def create(ctid: str, template: str | None = None):
    """
    Create OpenVZ containers.

    + ctid: CTID of the container to create
    """

    # Check we don't already have a container with this CTID
    current_containers = host.get_fact(OpenvzContainers)
    if ctid in current_containers:
        raise OperationError(
            f"An OpenVZ container with CTID {ctid} already exists",
        )

    command: list[str | QuoteString] = ["vzctl create", QuoteString(str(ctid))]

    if template:
        command += ["--ostemplate", QuoteString(template)]

    yield StringCommand(*command)


@operation(is_idempotent=False)
def set(ctid: str, save=True, **settings):
    """
    Set OpenVZ container details.

    + ctid: CTID of the container to set
    + save: whether to save the changes
    + settings: settings/arguments to apply to the container

    Settings/arguments:
        these are mapped directly to ``vztctl`` arguments, eg
        ``hostname='my-host.net'`` becomes ``--hostname my-host.net``.
    """

    command: list[str | QuoteString] = ["vzctl set", QuoteString(str(ctid))]

    if save:
        command.append("--save")

    # Both keys and values come from **settings and are user-controlled, so quote
    # both. shlex.quote leaves normal flags like --hostname untouched.
    for key, value in settings.items():
        # Handle list values (e.g. --nameserver X --nameserver X)
        if isinstance(value, list):
            for v in value:
                command += [QuoteString(f"--{key}"), QuoteString(str(v))]
        else:
            command += [QuoteString(f"--{key}"), QuoteString(str(value))]

    yield StringCommand(*command)
