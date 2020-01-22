import six

from . import ansible, docker, local, mech, ssh, vagrant, winrm


# Connectors that handle execution of pyinfra operations
EXECUTION_CONNECTORS = {  # pragma: no cover
    'docker': docker,
    'local': local,
    'ssh': ssh,
    'winrm': winrm,
}

# Connectors that handle generation of inventories
INVENTORY_CONNECTORS = {  # pragma: no cover
    'docker': docker,
    'mech': mech,
    'vagrant': vagrant,
    'ansible': ansible,
}

ALL_CONNECTORS = (  # pragma: no cover
    list(six.iterkeys(EXECUTION_CONNECTORS))
    + list(six.iterkeys(INVENTORY_CONNECTORS))
)
