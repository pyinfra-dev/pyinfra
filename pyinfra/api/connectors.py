import pkg_resources


class BaseConnectorMeta:
    handles_execution = False
    keys_prefix = ""

    class DataKeys:
        pass

    @classmethod
    def keys(cls):
        class Keys:
            pass

        for key in cls.DataKeys.__dict__:
            if not key.startswith("_"):
                setattr(Keys, key, f"{cls.keys_prefix}_{key}")

        return Keys


def _load_connector(entrypoint):
    connector = entrypoint.load()
    if not getattr(connector, "Meta", None):
        connector.Meta = BaseConnectorMeta
    return connector


def get_all_connectors():
    return {
        entrypoint.name: _load_connector(entrypoint)
        for entrypoint in pkg_resources.iter_entry_points("pyinfra.connectors")
    }


def get_execution_connectors():
    return {
        connector: connector_mod
        for connector, connector_mod in get_all_connectors().items()
        if connector_mod.Meta.handles_execution
    }


def get_execution_connector(name):
    return get_execution_connectors()[name]
