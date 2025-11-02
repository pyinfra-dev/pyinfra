try:
    from importlib_metadata import entry_points
except ImportError:
    from importlib.metadata import entry_points  # type: ignore[assignment]


def _load_connector(entrypoint):
    return entrypoint.load()


def get_all_connectors():
    return {
        entrypoint.name: _load_connector(entrypoint)
        for entrypoint in entry_points(group="pyinfra.connectors")
    }


def get_execution_connectors():
    return {
        connector: connector_mod
        for connector, connector_mod in get_all_connectors().items()
        if connector_mod.handles_execution
    }


def get_execution_connector(name):
    return get_execution_connectors()[name]
