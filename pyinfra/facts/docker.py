import json

from pyinfra.api import FactBase


class DockerFactBase(FactBase):
    abstract = True

    def process(self, output):
        output = ''.join(output)
        return json.loads(output)


class DockerSystemInfo(DockerFactBase):
    '''
    Returns ``docker system info`` output in JSON format.
    '''

    command = 'which docker > /dev/null && docker system info --format="{{json .}}" || true'


# All Docker objects
#

class DockerContainers(DockerFactBase):
    '''
    Returns ``docker inspect`` output for all Docker containers.
    '''

    command = 'which docker > /dev/null && docker container inspect `docker ps -qa` || true'


class DockerImages(DockerFactBase):
    '''
    Returns ``docker inspect`` output for all Docker images.
    '''

    command = 'which docker > /dev/null && docker image inspect `docker images -q` || true'


class DockerNetworks(DockerFactBase):
    '''
    Returns ``docker inspect`` output for all Docker networks.
    '''

    command = 'which docker > /dev/null && docker network inspect `docker network ls -q` || true'


# Single Docker objects
#

class DockerSingleMixin(DockerFactBase):
    def command(self, object_id):
        return 'which docker > /dev/null && docker {0} inspect {1} || true'.format(
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
