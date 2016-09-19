# pyinfra
# File: pyinfra/modules/lxd.py
# Desc: manage LXD containers

'''
The LXD modules manage LXD containers
'''

from __future__ import unicode_literals

from pyinfra.api import operation


def get_container_named(name, containers):
    for container in containers:
        if container['name'] == name:
            return container
    else:
        return None


@operation
def container(
    state, host, name,
    present=True, image='ubuntu:16.04'
):
    '''
    Manage LXD containers.

    Note: does not check if an existing container is based on the specified
    image.

    + name: name of the container
    + image: image to base the container on
    + present: whether the container should be present or absent
    '''

    container = get_container_named(name, host.fact.lxd_containers)

    if container:
        if present:
            # Not removing the container if it should be present:
            return []
        else:
            commands = []
            if container['status'] == 'Running':
                commands.append('lxc stop {0}'.format(name))

            # Command to remove the container:
            commands.append('lxc delete {0}'.format(name))
            return commands
    else:
        if not present:
            # Not creating the container if it should be absent:
            return []
        else:
            # Command to create the container:
            return [
                'lxc launch {image} {name}'.format(name=name, image=image)
            ]
