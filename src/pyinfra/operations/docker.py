"""
Manager Docker containers, volumes and networks. These operations allow you to manage Docker from
the view of the current inventory host. See the :doc:`../connectors/docker` to use Docker containers
as inventory directly.
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import OperationError, QuoteString, StringCommand, operation
from pyinfra.facts.docker import (
    DockerContainer,
    DockerImage,
    DockerNetwork,
    DockerPlugin,
    DockerVolume,
)

from .util.docker import ContainerSpec, handle_docker, parse_image_reference


@operation()
def container(
    container: str,
    image: str = "",
    ports: list[str] | None = None,
    networks: list[str] | None = None,
    volumes: list[str] | None = None,
    env_vars: list[str] | None = None,
    env_files: list[str] | None = None,
    labels: list[str] | None = None,
    pull_always: bool = False,
    present: bool = True,
    force: bool = False,
    start: bool = True,
    restart_policy: str | None = None,
    auto_remove: bool = False,
    mounts: list[str] | None = None,
    privileged: bool = False,
    hostname: str | None = None,
    entrypoint: str | None = None,
    user: str | None = None,
    cpus: float | None = None,
    memory: str | None = None,
    extra_args: list[str] | None = None,
    dns: list[str] | None = None,
):
    """
    Manage Docker containers

    + container: name to identify the container
    + image: container image and tag ex: nginx:alpine
    + networks: network list to attach on container
    + ports: port list to expose
    + volumes: volume list to map on container
    + env_vars: environment variable list to inject on container
    + env_files: list of files containing environment variables to inject on container
    + labels: Label list to attach to the container
    + pull_always: force image pull
    + force: remove a container with same name and create a new one
    + present: whether the container should be up and running
    + start: start or stop the container
    + restart_policy: restart policy to apply when a container exits
    + auto_remove: automatically remove the container and its associated anonymous volumes when it exits
    + mounts: list of ``--mount`` specifications (e.g. ``type=bind,source=/src,target=/app``)
    + privileged: give extended privileges to the container
    + hostname: container hostname
    + entrypoint: override the default entrypoint
    + user: username or UID to run as
    + cpus: number of CPUs (e.g. ``1.5``)
    + memory: memory limit (e.g. ``512m``, ``1g``)
    + extra_args: list of additional raw arguments passed to ``docker container create``
    + dns: list of dns servers to be used by the container

    **Examples:**

    .. code:: python

        from pyinfra.operations import docker
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
            restart_policy="unless-stopped",
            auto_remove=True,
        )

        # Run a container with mounts and resource limits
        docker.container(
            name="Deploy app container",
            container="myapp",
            image="myapp:latest",
            mounts=["type=bind,source=/host/data,target=/app/data"],
            privileged=True,
            hostname="myapp-host",
            entrypoint="/bin/sh",
            user="1000:1000",
            cpus=2.0,
            memory="512m",
            extra_args=["--cap-add", "NET_ADMIN"],
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
        env_files or list(),
        labels or list(),
        pull_always,
        restart_policy,
        auto_remove,
        mounts or list(),
        privileged,
        hostname,
        entrypoint,
        user,
        cpus,
        memory,
        extra_args or list(),
        dns or list(),
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


@operation()
def image(image: str, present: bool = True, force: bool = False):
    """
    Manage Docker images

    + image: Image and tag ex: nginx:alpine
    + present: whether the Docker image should exist
    + force: always pull the image if present is True

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
    image_info = parse_image_reference(image)
    if present:
        if force:
            # always pull the image if force is True
            yield handle_docker(
                resource="image",
                command="pull",
                image=image,
            )
            return
        else:
            existent_image = host.get_fact(DockerImage, object_id=image)
            if image_info.digest:
                # If a digest is specified, we must ensure the exact image is present
                if existent_image:
                    host.noop(f"Image with digest {image_info.digest} already exists!")
                else:
                    yield handle_docker(
                        resource="image",
                        command="pull",
                        image=image,
                    )
            elif image_info.tag == "latest" or not image_info.tag:
                # If the tag is 'latest' or not specified, always pull to ensure freshness
                yield handle_docker(
                    resource="image",
                    command="pull",
                    image=image,
                )
            else:
                # For other tags, check if the image exists
                if existent_image:
                    host.noop(f"Image with tag {image_info.tag} already exists!")
                else:
                    yield handle_docker(
                        resource="image",
                        command="pull",
                        image=image,
                    )
    else:
        existent_image = host.get_fact(DockerImage, object_id=image)
        if existent_image:
            yield handle_docker(
                resource="image",
                command="remove",
                image=image,
            )
        else:
            host.noop("There is no {0} image!".format(image))


@operation()
def build(
    path: str,
    tags: str | list[str] | None = None,
    dockerfile: str | None = None,
    build_args: dict[str, str] | None = None,
    labels: dict[str, str] | None = None,
    target: str | None = None,
    platform: str | None = None,
    network: str | None = None,
    cache_from: str | list[str] | None = None,
    secrets: list[str] | None = None,
    pull: bool = False,
    no_cache: bool = False,
    force: bool = False,
    builder: str = "docker build",
):
    """
    Build a Docker image from a context directory or URL.

    + path: build context (local directory or git/http URL)
    + tags: tag or list of tags to apply to the built image (maps to ``-t``)
    + dockerfile: path to the Dockerfile (maps to ``-f``; relative to the context)
    + build_args: ``--build-arg`` values as a mapping
    + labels: ``--label`` values as a mapping
    + target: ``--target`` stage for multi-stage Dockerfiles
    + platform: ``--platform`` (e.g. ``linux/amd64``)
    + network: ``--network`` (e.g. ``host``)
    + cache_from: image or list of images for ``--cache-from``
    + secrets: list of raw ``--secret`` specs (e.g. ``id=mysecret,src=/run/secret``)
    + pull: pass ``--pull`` to always fetch newer base images
    + no_cache: pass ``--no-cache``
    + force: rebuild even if all provided tags already exist locally
    + builder: builder command to invoke; use ``"docker buildx build"`` for BuildKit

    Idempotency is tag-based: when ``tags`` is provided and ``force`` is false, the
    operation no-ops if every tag already exists on the target. Without ``tags``
    the build always runs (Docker's own layer cache still applies).

    **Examples:**

    .. code:: python

        from pyinfra.operations import docker

        # Build and tag a local context
        docker.build(
            name="Build app image",
            path="/srv/app",
            tags=["app:1.0", "app:latest"],
            build_args={"VERSION": "1.0"},
            pull=True,
        )

        # BuildKit cross-platform build from a custom Dockerfile
        docker.build(
            name="Build multi-arch app",
            path="/srv/app",
            tags="registry.io/app:arm64",
            dockerfile="docker/Dockerfile.prod",
            platform="linux/arm64",
            builder="docker buildx build",
        )
    """
    if not path:
        raise OperationError("docker.build requires a context path")

    tag_list: list[str] = (
        [tags] if isinstance(tags, str) else list(tags) if tags is not None else []
    )
    cache_from_list: list[str] = (
        [cache_from]
        if isinstance(cache_from, str)
        else list(cache_from)
        if cache_from is not None
        else []
    )

    if tag_list and not force:
        missing = [tag for tag in tag_list if not host.get_fact(DockerImage, object_id=tag)]
        if not missing:
            host.noop("Image(s) {0} already exist!".format(", ".join(tag_list)))
            return

    command_bits: list = [builder]
    for tag in tag_list:
        command_bits.extend(["-t", QuoteString(tag)])
    if dockerfile:
        command_bits.extend(["-f", QuoteString(dockerfile)])
    for key, value in (build_args or {}).items():
        command_bits.extend(["--build-arg", QuoteString("{0}={1}".format(key, value))])
    for key, value in (labels or {}).items():
        command_bits.extend(["--label", QuoteString("{0}={1}".format(key, value))])
    if target:
        command_bits.extend(["--target", QuoteString(target)])
    if platform:
        command_bits.extend(["--platform", QuoteString(platform)])
    if network:
        command_bits.extend(["--network", QuoteString(network)])
    for cache in cache_from_list:
        command_bits.extend(["--cache-from", QuoteString(cache)])
    for secret in secrets or []:
        command_bits.extend(["--secret", QuoteString(secret)])
    if pull:
        command_bits.append("--pull")
    if no_cache:
        command_bits.append("--no-cache")
    command_bits.append(QuoteString(path))

    yield StringCommand(*command_bits)


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
