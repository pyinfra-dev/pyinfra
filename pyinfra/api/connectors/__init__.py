from . import ansible, docker, local, mech, ssh, vagrant, winrm


# Connectors that handle execution of pyinfra operations
EXECUTION_CONNECTORS = {  # pragma: no cover
    'docker': docker,
    'local': local,
    'ssh': ssh,
    'winrm': winrm,
}

# Connectors that handle generation of inventories
ALL_CONNECTORS = {  # pragma: no cover
    'ansible': ansible,
    'docker': docker,
    'local': local,
    'mech': mech,
    'ssh': ssh,
    'vagrant': vagrant,
    'winrm': winrm,
}
