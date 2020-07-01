import pkg_resources

# Connectors that handle generation of inventories
ALL_CONNECTORS = {
    ep.name: ep.load()
    for ep in pkg_resources.iter_entry_points('pyinfra.connectors')
}


# Connectors that handle execution of pyinfra operations
EXECUTION_CONNECTORS = {
    connector: connector_mod
    for connector, connector_mod in ALL_CONNECTORS.items()
    if getattr(connector_mod, 'EXECUTION_CONNECTOR', False)
}
