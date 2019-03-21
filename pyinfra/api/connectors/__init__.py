import six

from . import docker, local, ssh, vagrant


# Connectors that handle execution of pyinfra operations
EXECUTION_CONNECTORS = {
    'docker': docker,
    'local': local,
    'ssh': ssh,
}

# Connectors that handle generation of inventories
INVENTORY_CONNECTORS = {
    'docker': docker,
    'vagrant': vagrant,
}

ALL_CONNECTORS = (
    list(six.iterkeys(EXECUTION_CONNECTORS))
    + list(six.iterkeys(INVENTORY_CONNECTORS))
)
