from . import ansible, docker, local, mech, ssh, vagrant


# Connectors that handle execution of pyinfra operations
EXECUTION_CONNECTORS = {  # pragma: no cover
    'docker': docker,
    'local': local,
    'ssh': ssh,
}

# Connectors that handle generation of inventories
INVENTORY_CONNECTORS = {  # pragma: no cover
    'docker': docker,
    'mech': mech,
    'vagrant': vagrant,
    'ansible': ansible,
}

ALL_CONNECTORS = (  # pragma: no cover
    list(EXECUTION_CONNECTORS.keys())
    + list(INVENTORY_CONNECTORS.keys())
)
