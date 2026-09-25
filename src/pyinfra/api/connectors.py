try:
    from importlib_metadata import entry_points
except ImportError:
    from importlib.metadata import entry_points  # type: ignore[assignment]

from pyinfra import logger

from .exceptions import NoConnectorError


# Connectors already reported as unloadable: the registry is rebuilt on every lookup (once
# per inventory, again per host), so warn once per process rather than once per lookup.
_reported_broken_connectors: set[str] = set()


def _load_connector(entrypoint):
    try:
        return entrypoint.load()
    except Exception as e:
        # A connector that cannot be imported - a package uninstalled while its entry point
        # metadata remains, a missing dependency, an editable install recording entry points
        # from another branch - must not make pyinfra unusable for every other connector.
        # Report it here, and again with its cause if one of the deploys asks for it (see
        # `invalid_connector_error`).
        if entrypoint.name not in _reported_broken_connectors:
            _reported_broken_connectors.add(entrypoint.name)
            logger.warning(
                "Ignoring the '%s' connector, it could not be loaded: %s", entrypoint.name, e
            )
        return None


def get_all_connectors():
    connectors = {}

    for entrypoint in entry_points(group="pyinfra.connectors"):
        connector = _load_connector(entrypoint)
        if connector is not None:
            connectors[entrypoint.name] = connector

    return connectors


def get_execution_connectors():
    return {
        connector: connector_mod
        for connector, connector_mod in get_all_connectors().items()
        if connector_mod.handles_execution
    }


def get_execution_connector(name):
    try:
        return get_execution_connectors()[name]
    except KeyError:
        raise invalid_connector_error(name) from None


def connector_load_error(name: str) -> Exception | None:
    """
    Return why the connector ``name`` cannot be imported, or None if it is simply not
    installed - or loads fine.

    Connectors that fail to load are skipped by `get_all_connectors`, so that one broken
    package cannot take every other connector down with it. This retrieves the cause, for
    the point where that name is actually requested.

    + param name: connector name, as used in an inventory (``@name``).
    """

    for entrypoint in entry_points(group="pyinfra.connectors"):
        if entrypoint.name != name:
            continue

        try:
            entrypoint.load()
        except Exception as e:
            return e

        return None

    return None


def invalid_connector_error(name: str) -> NoConnectorError:
    """
    Build the error for a connector name that is not available, naming the cause when the
    connector is installed but could not be loaded.

    + param name: connector name, as used in an inventory (``@name``).
    """

    load_error = connector_load_error(name)

    if load_error is None:
        return NoConnectorError(f"Invalid connector: {name}")

    return NoConnectorError(
        f"Invalid connector: {name} (it is installed but could not be loaded: {load_error})",
    )
