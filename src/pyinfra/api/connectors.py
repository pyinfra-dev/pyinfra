import os
import shutil

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

    if "async-ssh" not in discovered:
        from pyinfra.connectors.asyncssh import AsyncSSHConnector

        discovered["async-ssh"] = AsyncSSHConnector

    # Backward-compatible aliases for async-ssh
    if "asyncssh" not in discovered:
        discovered["asyncssh"] = discovered["async-ssh"]

    if "ssh" not in discovered:
        discovered["ssh"] = discovered["async-ssh"]

    if "ssh-cli" not in discovered:
        from pyinfra.connectors.ssh_cli import SSHCLIConnector

        discovered["ssh-cli"] = SSHCLIConnector

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


def is_ssh_cli_available() -> bool:
    return shutil.which("ssh") is not None and shutil.which("scp") is not None


def get_default_ssh_connector_name(execution_connectors=None) -> str:
    execution_connectors = execution_connectors or get_execution_connectors()

    connector_name = os.environ.get("PYINFRA_SSH_CONNECTOR")
    if connector_name:
        return connector_name.strip().lstrip("@")

    if "ssh-cli" in execution_connectors and is_ssh_cli_available():
        return "ssh-cli"

    if "async-ssh" in execution_connectors:
        return "async-ssh"

    if "ssh" in execution_connectors:
        return "ssh"

    return next(iter(execution_connectors))
