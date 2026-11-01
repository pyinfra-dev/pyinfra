try:
    from importlib_metadata import entry_points
except ImportError:
    from importlib.metadata import entry_points  # type: ignore[assignment]

from .exceptions import NoConnectorError


def _entry_points():
    return entry_points(group="pyinfra.connectors")


def get_connector(name: str):
    """
    Return the connector registered under ``name``, importing it.

    Only the connector asked for is imported. A package whose module cannot be imported
    therefore costs nothing until something actually asks for it - and when it does, the error
    names both the connector and the cause, instead of taking the other connectors down with it.

    + param name: connector name, as used in an inventory (``@name``).
    """

    for entrypoint in _entry_points():
        if entrypoint.name != name:
            continue

        try:
            return entrypoint.load()
        except Exception as e:
            raise NoConnectorError(
                f"Invalid connector: {name} (it is installed but could not be loaded: {e})",
            ) from e

    raise NoConnectorError(f"Invalid connector: {name}")


def get_all_connectors():
    return {entrypoint.name: entrypoint.load() for entrypoint in _entry_points()}


def get_execution_connectors():
    """
    Return every installed connector that can execute commands.

    Imports all of them, so prefer ``get_execution_connector`` when only one is wanted.
    """

    return {
        name: connector
        for name, connector in get_all_connectors().items()
        if connector.handles_execution
    }


def get_execution_connector(name: str):
    """
    Return the connector registered under ``name`` that can execute commands.

    Only this connector is imported, unlike ``get_execution_connectors``.

    + param name: connector name, as used in an inventory (``@name``).
    """

    connector = get_connector(name)

    if not connector.handles_execution:
        raise NoConnectorError(
            f"Invalid connector: {name} (it cannot execute commands, it only provides names)",
        )

    return connector
