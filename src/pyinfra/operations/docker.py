"""
Manager Docker containers, volumes and networks. These operations allow you to manage Docker from
the view of the current inventory host. See the :doc:`../connectors/docker` to use Docker containers
as inventory directly.
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.docker import DockerContainer, DockerNetwork, DockerPlugin, DockerVolume

from .util.docker import ContainerSpec, handle_docker


@operation()
def container(
    container: str,
    image: str = "",
    ports: list[str] | None = None,
    networks: list[str] | None = None,
    volumes: list[str] | None = None,
    env_vars: list[str] | None = None,
    pull_always: bool = False,
    present: bool = True,
    force: bool = False,
    start: bool = True,
):
    """
    Manage Docker containers

    + container: name to identify the container
    + image: container image and tag ex: nginx:alpine
    + networks: network list to attach on container
    + ports: port list to expose
    + volumes: volume list to map on container
    + env_vars: environment variable list to inject on container
    + pull_always: force image pull
    + force: remove a container with same name and create a new one
    + present: whether the container should be up and running
    + start: start or stop the container

    **Examples:**

    .. code:: python

        # Run a container
        docker.container(
            name="Deploy Nginx container",
            container="nginx",
            image="nginx:alpine",
            ports=["80:80"],
            present=True,
            force=True,
            networks=["proxy", "services"],
            volumes=["nginx_data:/usr/share/nginx/html"],
            pull_always=True,
        )

        # Stop a container
        docker.container(
            name="Stop Nginx container",
            container="nginx",
            start=False,
        )

        # Start a container
        docker.container(
            name="Start Nginx container",
            container="nginx",
            start=True,
        )
    """

    want_spec = ContainerSpec(
        image,
        ports or list(),
        networks or list(),
        volumes or list(),
        env_vars or list(),
        pull_always,
    )
    existent_container = host.get_fact(DockerContainer, object_id=container)

    container_spec_changes = want_spec.diff_from_inspect(existent_container)

    is_running = (
        (existent_container[0]["State"]["Status"] == "running")
        if existent_container and existent_container[0]
        else False
    )
    recreating = existent_container and (force or container_spec_changes)
    removing = existent_container and not present

    do_remove = recreating or removing
    do_create = (present and not existent_container) or recreating
    do_start = start and (recreating or not is_running)
    do_stop = not start and not removing and is_running

    if do_remove:
        yield handle_docker(
            resource="container",
            command="remove",
            container=container,
        )

    if do_create:
        yield handle_docker(
            resource="container",
            command="create",
            container=container,
            spec=want_spec,
        )

    if do_start:
        yield handle_docker(
            resource="container",
            command="start",
            container=container,
        )

    if do_stop:
        yield handle_docker(
            resource="container",
            command="stop",
            container=container,
        )


@operation(is_idempotent=False)
def image(image, present=True):
    """
    Manage Docker images

    + image: Image and tag ex: nginx:alpine
    + present: whether the Docker image should exist

    **Examples:**

    .. code:: python

        # Pull a Docker image
        docker.image(
            name="Pull nginx image",
            image="nginx:alpine",
            present=True,
        )

        # Remove a Docker image
        docker.image(
            name="Remove nginx image",
            image:"nginx:image",
            present=False,
        )
    """

    if present:
        yield handle_docker(
            resource="image",
            command="pull",
            image=image,
        )

    else:
        yield handle_docker(
            resource="image",
            command="remove",
            image=image,
        )


@operation()
def volume(volume: str, driver: str = "", labels: list[str] | None = None, present: bool = True):
    """
    Manage Docker volumes

    + volume: Volume name
    + driver: Docker volume storage driver
    + labels: Label list to attach in the volume
    + present: whether the Docker volume should exist

    **Examples:**

    .. code:: python

        # Create a Docker volume
        docker.volume(
            name="Create nginx volume",
            volume="nginx_data",
            present=True
        )
    """

    existent_volume = host.get_fact(DockerVolume, object_id=volume)

    if present:

        if existent_volume:
            host.noop("Volume already exists!")
            return

        yield handle_docker(
            resource="volume",
            command="create",
            volume=volume,
            driver=driver,
            labels=labels,
            present=present,
        )

    else:
        if existent_volume is None:
            host.noop("There is no {0} volume!".format(volume))
            return

        yield handle_docker(
            resource="volume",
            command="remove",
            volume=volume,
        )


@operation()
def network(
    network: str,
    driver: str = "",
    gateway: str = "",
    ip_range: str = "",
    ipam_driver: str = "",
    subnet: str = "",
    scope: str = "",
    aux_addresses: dict[str, str] | None = None,
    opts: list[str] | None = None,
    ipam_opts: list[str] | None = None,
    labels: list[str] | None = None,
    ingress: bool = False,
    attachable: bool = False,
    present: bool = True,
):
    """
    Manage docker networks

    + network: Network name
    + driver: Network driver ex: bridge or overlay
    + gateway: IPv4 or IPv6 Gateway for the master subnet
    + ip_range: Allocate container ip from a sub-range
    + ipam_driver: IP Address Management Driver
    + subnet: Subnet in CIDR format that represents a network segment
    + scope: Control the network's scope
    + aux_addresses: named aux addresses for the network
    + opts: Set driver specific options
    + ipam_opts: Set IPAM driver specific options
    + labels: Label list to attach in the network
    + ingress: Create swarm routing-mesh network
    + attachable: Enable manual container attachment
    + present: whether the Docker network should exist

    **Examples:**

    .. code:: python

        # Create Docker network
        docker.network(
            network="nginx",
            attachable=True,
            present=True,
        )
    """
    existent_network = host.get_fact(DockerNetwork, object_id=network)

    if present:
        if existent_network:
            host.noop("Network {0} already exists!".format(network))
            return

        yield handle_docker(
            resource="network",
            command="create",
            network=network,
            driver=driver,
            gateway=gateway,
            ip_range=ip_range,
            ipam_driver=ipam_driver,
            subnet=subnet,
            scope=scope,
            aux_addresses=aux_addresses,
            opts=opts,
            ipam_opts=ipam_opts,
            labels=labels,
            ingress=ingress,
            attachable=attachable,
            present=present,
        )

    else:
        if existent_network is None:
            host.noop("Network {0} does not exist!".format(network))
            return

        yield handle_docker(
            resource="network",
            command="remove",
            network=network,
        )


@operation(is_idempotent=False)
def prune(
    all: bool = False,
    volumes: bool = False,
    filter: str = "",
):
    """
    Execute a docker system prune.

    + all: Remove all unused images not just dangling ones
    + volumes: Prune anonymous volumes
    + filter: Provide filter values (e.g. "label=<key>=<value>" or "until=24h")

    **Examples:**

    .. code:: python

        # Remove dangling images
        docker.prune(
            name="remove dangling images",
        )

        # Remove all images and volumes
        docker.prune(
            name="Remove all images and volumes",
            all=True,
            volumes=True,
        )

        # Remove images older than 90 days
        docker.prune(
            name="Remove unused older than 90 days",
            filter="until=2160h"
        )
    """

    yield handle_docker(
        resource="system",
        command="prune",
        all=all,
        volumes=volumes,
        filter=filter,
    )


@operation()
def plugin(
    plugin: str,
    alias: str | None = None,
    present: bool = True,
    enabled: bool = True,
    plugin_options: dict[str, str] | None = None,
):
    """
    Manage Docker plugins

    + plugin: Plugin name
    + alias: Alias for the plugin (optional)
    + present: Whether the plugin should be installed
    + enabled: Whether the plugin should be enabled
    + plugin_options: Options to pass to the plugin

    **Examples:**

    .. code:: python

        # Install and enable a Docker plugin
        docker.plugin(
            name="Install and enable a Docker plugin",
            plugin="username/my-awesome-plugin:latest",
            alias="my-plugin",
            present=True,
            enabled=True,
            plugin_options={"option1": "value1", "option2": "value2"},
        )
    """
    plugin_name = alias if alias else plugin
    existent_plugin = host.get_fact(DockerPlugin, object_id=plugin_name)
    if existent_plugin:
        existent_plugin = existent_plugin[0]

    if present:
        if existent_plugin:
            plugin_options_different = (
                plugin_options and existent_plugin["Settings"]["Env"] != plugin_options
            )
            if plugin_options_different:
                # Update options on existing plugin
                if existent_plugin["Enabled"]:
                    yield handle_docker(
                        resource="plugin",
                        command="disable",
                        plugin=plugin_name,
                    )
                yield handle_docker(
                    resource="plugin",
                    command="set",
                    plugin=plugin_name,
                    enabled=enabled,
                    existent_options=existent_plugin["Settings"]["Env"],
                    required_options=plugin_options,
                )
                if enabled:
                    yield handle_docker(
                        resource="plugin",
                        command="enable",
                        plugin=plugin_name,
                    )
            else:
                # Options are the same, check if enabled state is different
                if existent_plugin["Enabled"] == enabled:
                    host.noop(
                        f"Plugin '{plugin_name}' is already installed with the same options "
                        f"and {'enabled' if enabled else 'disabled'}."
                    )
                    return
                else:
                    command = "enable" if enabled else "disable"
                    yield handle_docker(
                        resource="plugin",
                        command=command,
                        plugin=plugin_name,
                    )
        else:
            yield handle_docker(
                resource="plugin",
                command="install",
                plugin=plugin,
                alias=alias,
                enabled=enabled,
                plugin_options=plugin_options,
            )
    else:
        if not existent_plugin:
            host.noop(f"Plugin '{plugin_name}' is not installed.")
            return
        yield handle_docker(
            resource="plugin",
            command="remove",
            plugin=plugin_name,
        )
