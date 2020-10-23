import json

from pyinfra.api import FactBase


class DockerFactBase(FactBase):
    abstract = True

    requires_command = 'docker'

    def process(self, output):
        output = ''.join(output)
        return json.loads(output)


class DockerSystemInfo(DockerFactBase):
    '''
    Returns ``docker system info`` output in JSON format.
    '''

    command = 'docker system info --format="{{json .}}"'


# All Docker objects
#

class DockerContainers(DockerFactBase):
    '''
    Returns ``docker inspect`` output for all Docker containers.
    '''

    command = 'docker container inspect `docker ps -qa`'


class DockerImages(DockerFactBase):
    '''
    Returns ``docker inspect`` output for all Docker images.
    '''

    command = 'docker image inspect `docker images -q`'


class DockerNetworks(DockerFactBase):
    '''
    Returns ``docker inspect`` output for all Docker networks.
    '''

    command = 'docker network inspect `docker network ls -q`'


# Single Docker objects
#

class DockerSingleMixin(DockerFactBase):
    def command(self, object_id):
        return 'docker {0} inspect {1}'.format(
            self.docker_type, object_id,
        )


class DockerContainer(DockerSingleMixin):
    '''
    Returns ``docker inspect`` output for a single Docker container.
    '''

    docker_type = 'container'


class DockerImage(DockerSingleMixin):
    '''
    Returns ``docker inspect`` output for a single Docker image.
    '''

    docker_type = 'image'


class DockerNetwork(DockerSingleMixin):
    '''
    Returns ``docker inspect`` output for a single Docker network.
    '''

    docker_type = 'network'
