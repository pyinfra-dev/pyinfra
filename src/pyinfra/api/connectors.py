try:
    from importlib_metadata import entry_points
except ImportError:
    from importlib.metadata import entry_points  # type: ignore[assignment]


def _load_connector(entrypoint):
    return entrypoint.load()


def get_all_connectors():
    discovered = {
        entrypoint.name: _load_connector(entrypoint)
        for entrypoint in entry_points(group="pyinfra.connectors")
    }

    if "ssh" not in discovered:
        from pyinfra.connectors.ssh import SSHConnector

        discovered["ssh"] = SSHConnector

    if "local" not in discovered:
        from pyinfra.connectors.local import LocalConnector

        discovered["local"] = LocalConnector

    if "docker" not in discovered:
        from pyinfra.connectors.docker import DockerConnector

        discovered["docker"] = DockerConnector

    if "podman" not in discovered:
        from pyinfra.connectors.docker import PodmanConnector

        discovered["podman"] = PodmanConnector

    if "dockerssh" not in discovered:
        from pyinfra.connectors.dockerssh import DockerSSHConnector

        discovered["dockerssh"] = DockerSSHConnector

    if "chroot" not in discovered:
        from pyinfra.connectors.chroot import ChrootConnector

        discovered["chroot"] = ChrootConnector

    return discovered


def get_execution_connectors():
    return {
        connector: connector_mod
        for connector, connector_mod in get_all_connectors().items()
        if connector_mod.handles_execution
    }


def get_execution_connector(name):
    return get_execution_connectors()[name]
