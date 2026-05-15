"""
Facts about Docker containers, volumes and networks. These facts give you information from the view
of the current inventory host. See the :doc:`../connectors/docker` to use Docker containers as
inventory directly.
"""

from __future__ import annotations

import json

from typing_extensions import override

from pyinfra.api import FactBase, ShortFactBase


class DockerFactBase(FactBase):
    abstract = True

    docker_type: str

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "docker"

    @override
    def process(self, output):
        output = "".join(output)
        return json.loads(output)


class _DockerJsonLinesFactBase(FactBase):
    abstract = True

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "docker"

    @override
    def process(self, output):
        return [json.loads(line) for line in output if line.strip()]


class DockerSystemInfo(DockerFactBase):
    """
    Returns ``docker system info`` output in JSON format.
    """

    @override
    def command(self) -> str:
        return 'docker system info --format="{{json .}}"'


class DockerVersion(FactBase[str]):
    """
    Returns the Docker version.
    """

    @override
    def requires_command(self) -> str:
        return "docker"

    @override
    def command(self) -> str:
        return "docker --version"

    @override
    def process(self, output):
        return "".join(output).replace("\n", "")


# All Docker objects
#


class DockerContainers(DockerFactBase):
    """
    Returns ``docker inspect`` output for all Docker containers.
    """

    @override
    def command(self) -> str:
        return """
        ids=$(docker ps -qa) && [ -n "$ids" ] && docker container inspect $ids || echo "[]"
        """.strip()


class DockerImages(DockerFactBase):
    """
    Returns ``docker inspect`` output for all Docker images.
    """

    @override
    def command(self) -> str:
        return """
        ids=$(docker images -q) && [ -n "$ids" ] && docker image inspect $ids || echo "[]"
        """.strip()


class DockerNetworks(DockerFactBase):
    """
    Returns ``docker inspect`` output for all Docker networks.
    """

    @override
    def command(self) -> str:
        return "docker network inspect `docker network ls -q`"


class DockerVolumes(DockerFactBase):
    """
    Returns ``docker inspect`` output for all Docker volumes.
    """

    @override
    def command(self) -> str:
        return "docker volume inspect `docker volume ls -q`"


class DockerPlugins(DockerFactBase):
    """
    Returns ``docker plugin inspect`` output for all Docker plugins.
    """

    @override
    def command(self) -> str:
        return """
        ids=$(docker plugin ls -q) && [ -n "$ids" ] && docker plugin inspect $ids || echo "[]"
        """.strip()


# Single Docker objects
#


class DockerSingleMixin(DockerFactBase):
    @override
    def command(self, object_id):
        return f"docker {self.docker_type} inspect {object_id} 2>&- || true"


class DockerContainer(DockerSingleMixin):
    """
    Returns ``docker inspect`` output for a single Docker container.
    """

    docker_type = "container"


class DockerImage(DockerSingleMixin):
    """
    Returns ``docker inspect`` output for a single Docker image.
    """

    docker_type = "image"


class DockerNetwork(DockerSingleMixin):
    """
    Returns ``docker inspect`` output for a single Docker network.
    """

    docker_type = "network"


class DockerVolume(DockerSingleMixin):
    """
    Returns ``docker inspect`` output for a single Docker container.
    """

    docker_type = "volume"


class DockerPlugin(DockerSingleMixin):
    """
    Returns ``docker plugin inspect`` output for a single Docker plugin.
    """

    docker_type = "plugin"


# Derived facts: extract specific slices from the full inspect output.
#


class DockerContainerEnvs(ShortFactBase):
    """
    Returns environment variables for all Docker containers, keyed by container ID.
    """

    fact = DockerContainers

    @override
    def process_data(self, data):
        result = {}
        for container in data or []:
            container_id = container.get("Id")
            env_list = (container.get("Config") or {}).get("Env") or []
            env: dict = {}
            for entry in env_list:
                key, _, value = entry.partition("=")
                env[key] = value
            result[container_id] = env
        return result


class DockerContainerLabels(ShortFactBase):
    """
    Returns labels for all Docker containers, keyed by container ID.
    """

    fact = DockerContainers

    @override
    def process_data(self, data):
        return {
            container.get("Id"): (container.get("Config") or {}).get("Labels") or {}
            for container in data or []
        }


class DockerContainerMounts(ShortFactBase):
    """
    Returns mounts for all Docker containers, keyed by container ID.
    """

    fact = DockerContainers

    @override
    def process_data(self, data):
        return {container.get("Id"): container.get("Mounts") or [] for container in data or []}


class DockerContainerNetworks(ShortFactBase):
    """
    Returns networks for all Docker containers, keyed by container ID.
    """

    fact = DockerContainers

    @override
    def process_data(self, data):
        return {
            container.get("Id"): ((container.get("NetworkSettings") or {}).get("Networks") or {})
            for container in data or []
        }


class DockerContainerPorts(ShortFactBase):
    """
    Returns published port bindings for all Docker containers, keyed by container ID.
    """

    fact = DockerContainers

    @override
    def process_data(self, data):
        return {
            container.get("Id"): ((container.get("NetworkSettings") or {}).get("Ports") or {})
            for container in data or []
        }


class DockerImageLabels(ShortFactBase):
    """
    Returns labels for all Docker images, keyed by image ID.
    """

    fact = DockerImages

    @override
    def process_data(self, data):
        return {
            image.get("Id"): (
                (image.get("Config") or {}).get("Labels")
                or (image.get("ContainerConfig") or {}).get("Labels")
                or {}
            )
            for image in data or []
        }


class DockerImageLayers(ShortFactBase):
    """
    Returns layer digests for all Docker images, keyed by image ID.
    """

    fact = DockerImages

    @override
    def process_data(self, data):
        return {
            image.get("Id"): (image.get("RootFS") or {}).get("Layers") or [] for image in data or []
        }


class DockerNetworkLabels(ShortFactBase):
    """
    Returns labels for all Docker networks, keyed by network ID.
    """

    fact = DockerNetworks

    @override
    def process_data(self, data):
        return {network.get("Id"): network.get("Labels") or {} for network in data or []}


class DockerVolumeLabels(ShortFactBase):
    """
    Returns labels for all Docker volumes, keyed by volume name.
    """

    fact = DockerVolumes

    @override
    def process_data(self, data):
        return {volume.get("Name"): volume.get("Labels") or {} for volume in data or []}


# Facts that need their own docker command.
#


class DockerContainerFsChanges(DockerFactBase):
    """
    Returns filesystem changes for a single container (``docker diff``) as a list of
    ``{"path": ..., "change": "A"|"C"|"D"}`` entries.
    """

    @override
    def command(self, container_id) -> str:
        return f"docker container diff {container_id} 2>&- || true"

    @override
    def process(self, output):
        changes = []
        for line in output:
            line = line.rstrip("\n")
            if not line or " " not in line:
                continue
            change, _, path = line.partition(" ")
            changes.append({"change": change, "path": path})
        return changes


class DockerContainerProcesses(DockerFactBase):
    """
    Returns processes running inside a single container (``docker top``) as a list of
    column dicts. Column names follow the ``ps`` output header.
    """

    @override
    def command(self, container_id) -> str:
        return f"docker container top {container_id} 2>&- || true"

    @override
    def process(self, output):
        lines = [line for line in (line.rstrip("\n") for line in output) if line]
        if not lines:
            return []
        header = lines[0].split()
        processes = []
        for line in lines[1:]:
            fields = line.split(None, len(header) - 1)
            if len(fields) < len(header):
                fields += [""] * (len(header) - len(fields))
            processes.append(dict(zip(header, fields)))
        return processes


class DockerContainerStats(_DockerJsonLinesFactBase):
    """
    Returns resource-usage stats for all running containers (``docker stats``) as a list
    of dicts (one entry per container).
    """

    @override
    def command(self) -> str:
        return "docker stats --no-stream --format '{{json .}}'"


class DockerImageHistory(_DockerJsonLinesFactBase):
    """
    Returns the layer history of a single image (``docker history``) as a list of dicts.
    """

    @override
    def command(self, image_id) -> str:
        return f"docker image history --no-trunc --format '{{{{json .}}}}' {image_id} 2>&- || true"


class DockerAuths(FactBase[list[str]]):
    """
    Returns the list of registry servers the current user is authenticated
    against, read from ``${DOCKER_CONFIG:-$HOME/.docker}/config.json``.

    Returns an empty list if no config file exists or no auths are stored.
    """

    @override
    def command(self) -> str:
        return (
            'config="${DOCKER_CONFIG:-$HOME/.docker}/config.json"; '
            '[ -r "$config" ] && cat "$config" || echo "{}"'
        )

    @override
    def process(self, output: list[str]) -> list[str]:
        try:
            data = json.loads("".join(output))
        except json.JSONDecodeError:
            return []
        return list(data.get("auths", {}).keys())
