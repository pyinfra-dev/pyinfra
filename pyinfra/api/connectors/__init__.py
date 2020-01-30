from . import ansible, docker, local, mech, ssh, vagrant


# Connectors that handle execution of pyinfra operations
EXECUTION_CONNECTORS = {  # pragma: no cover
    'docker': docker,
    'local': local,
    'ssh': ssh,
}

# Connectors that handle generation of inventories
ALL_CONNECTORS = {  # pragma: no cover
    'ansible': ansible,
    'docker': docker,
    'local': local,
    'mech': mech,
    'ssh': ssh,
    'vagrant': vagrant,
}
