"""
The LXD modules manage LXD containers
"""

from __future__ import annotations

from typing import Any

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.lxd import LxdContainers


def get_container_named(name: str, containers: list[dict[str, Any]]) -> dict[str, Any] | None:
    for container in containers:
        if container["name"] == name:
            return container
    return None


@operation()
def container(
    id: str,
    present=True,
    image="ubuntu:16.04",
):
    """
    Add/remove LXD containers.

    Note: does not check if an existing container is based on the specified
    image.

    + id: name/identifier for the container
    + image: image to base the container on
    + present: whether the container should be present or absent

    **Example:**

    .. code:: python

        lxd.container(
            name="Add an ubuntu container",
            id="ubuntu19",
            image="ubuntu:19.10",
        )
    """

    current_containers = host.get_fact(LxdContainers)
    container = get_container_named(id, current_containers)

    # Container exists and we don't want it
    if not present:
        if container:
            if container["status"] == "Running":
                yield "lxc stop {0}".format(id)

            # Command to remove the container:
            yield "lxc delete {0}".format(id)
        else:
            host.noop("container {0} does not exist".format(id))

    # Container doesn't exist and we want it
    if present:
        if not container:
            # Command to create the container:
            yield "lxc launch {image} {id} < /dev/null".format(id=id, image=image)
        else:
            host.noop("container {0} exists".format(id))
