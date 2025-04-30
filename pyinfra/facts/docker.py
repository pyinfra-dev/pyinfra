"""
Facts about Docker containers, volumes and networks. These facts give you information from the view
of the current inventory host. See the :doc:`../connectors/docker` to use Docker containers as
inventory directly.
"""

from __future__ import annotations

import json

from typing_extensions import override

from pyinfra.api import FactBase


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


class DockerSystemInfo(DockerFactBase):
    """
    Returns ``docker system info`` output in JSON format.
    """

    @override
    def command(self) -> str:
        return 'docker system info --format="{{json .}}"'


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


# Single Docker objects
#


class DockerSingleMixin(DockerFactBase):
    @override
    def command(self, object_id):
        return "docker {0} inspect {1} 2>&- || true".format(
            self.docker_type,
            object_id,
        )


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


class DockerVolumes(DockerFactBase):
    """
    Returns ``docker inspect`` output for all Docker volumes.
    """

    @override
    def command(self) -> str:
        return "docker volume inspect `docker volume ls -q`"


class DockerVolume(DockerSingleMixin):
    """
    Returns ``docker inspect`` output for a single Docker container.
    """

    docker_type = "volume"
