from . import local, ssh, vagrant


# Connectors that handle execution of pyinfra operations
EXECUTION_CONNECTORS = {
    'local': local,
    'ssh': ssh,
}

# Connectors that handle generation of inventories
INVENTORY_CONNECTORS = {
    'vagrant': vagrant,
}

ALL_CONNECTORS = EXECUTION_CONNECTORS.keys() + INVENTORY_CONNECTORS.keys()
