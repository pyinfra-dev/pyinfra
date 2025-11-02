"""
Manage OpenVZ containers with ``vzctl``.
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import OperationError, operation
from pyinfra.facts.vzctl import OpenvzContainers


@operation(is_idempotent=False)
def start(ctid: str, force=False):
    """
    Start OpenVZ containers.

    + ctid: CTID of the container to start
    + force: whether to force container start
    """

    args = ["{0}".format(ctid)]

    if force:
        args.append("--force")

    yield "vzctl start {0}".format(" ".join(args))


@operation(is_idempotent=False)
def stop(ctid: str):
    """
    Stop OpenVZ containers.

    + ctid: CTID of the container to stop
    """

    args = ["{0}".format(ctid)]

    yield "vzctl stop {0}".format(" ".join(args))


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

    yield "vzctl mount {0}".format(ctid)


@operation(is_idempotent=False)
def unmount(ctid: str):
    """
    Unmount OpenVZ container filesystems.

    + ctid: CTID of the container to unmount
    """

    yield "vzctl umount {0}".format(ctid)


@operation(is_idempotent=False)
def delete(ctid: str):
    """
    Delete OpenVZ containers.

    + ctid: CTID of the container to delete
    """

    yield "vzctl delete {0}".format(ctid)


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
            "An OpenVZ container with CTID {0} already exists".format(ctid),
        )

    args = ["{0}".format(ctid)]

    if template:
        args.append("--ostemplate {0}".format(template))

    yield "vzctl create {0}".format(" ".join(args))


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

    args = ["{0}".format(ctid)]

    if save:
        args.append("--save")

    for key, value in settings.items():
        # Handle list values (e.g. --nameserver X --nameserver X)
        if isinstance(value, list):
            args.extend("--{0} {1}".format(key, v) for v in value)
        else:
            args.append("--{0} {1}".format(key, value))

    yield "vzctl set {0}".format(" ".join(args))
