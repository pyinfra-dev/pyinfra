from dataclasses import dataclass, field
from typing import Any

from pyinfra.api import OperationError


@dataclass
class ImageReference:
    """Represents a parsed Docker image reference."""

    repository: str
    namespace: str | None = None
    tag: str | None = None
    digest: str | None = None
    registry_host: str | None = None
    registry_port: int | None = None

    @property
    def registry(self) -> str | None:
        """Get the full registry address (host:port)."""
        if not self.registry_host:
            return None
        if self.registry_port:
            return f"{self.registry_host}:{self.registry_port}"
        return self.registry_host

    @property
    def name(self) -> str:
        """Get the full image name without tag or digest."""
        parts = []
        if self.registry:
            parts.append(self.registry)
        if self.namespace:
            parts.append(self.namespace)
        parts.append(self.repository)
        return "/".join(parts)

    @property
    def full_reference(self) -> str:
        """Get the complete image reference string."""
        ref = self.name
        if self.tag:
            ref += f":{self.tag}"
        if self.digest:
            ref += f"@{self.digest}"
        return ref


def parse_registry(registry: str) -> tuple[str, int | None]:
    """
    Parse a registry string into host and port components.

    Args:
        registry: String like "registry.io:5000" or "registry.io"

    Returns:
        tuple: (host, port) where port is None if not specified

    Raises:
        ValueError: If port is specified but not a valid integer
    """
    if ":" in registry:
        host, port_str = registry.rsplit(":", 1)
        if port_str:  # Only try to parse if port_str is not empty
            try:
                port = int(port_str)
                if port < 0 or port > 65535:
                    raise ValueError(
                        f"Invalid port number: {port}. Port must be between 0 and 65535"
                    )
                return host, port
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(
                        f"Invalid port in registry '{registry}': '{port_str}' is not a valid port number"
                    )
                raise  # Re-raise port range error
        else:
            # Empty port (e.g., "registry.io:")
            raise ValueError(f"Invalid registry format '{registry}': port cannot be empty")
    else:
        return registry, None


def parse_image_reference(image: str) -> ImageReference:
    """
    Parse a Docker image reference into components.

    Format: [HOST[:PORT]/]NAMESPACE/REPOSITORY[:TAG][@DIGEST]

    Raises:
        ValueError: If the image reference is empty or invalid
    """
    if not image or not image.strip():
        raise ValueError("Image reference cannot be empty")

    original = image.strip()
    registry_host = None
    registry_port = None
    namespace = None
    repository = None
    tag = None
    digest = None

    # Extract digest first (format: name@digest)
    if "@" in original:
        original, digest = original.rsplit("@", 1)

    # Extract tag (format: name:tag)
    if ":" in original:
        parts = original.split(":")
        if len(parts) >= 2:
            potential_tag = parts[-1]
            # Tag cannot contain '/' - if it does, the colon is part of the registry, separating host and port
            if "/" not in potential_tag:
                original = ":".join(parts[:-1])
                tag = potential_tag

    # Split by '/' to separate registry/namespace/repository
    parts = original.split("/")

    if len(parts) == 1:
        # Just repository name (e.g., "nginx")
        repository = parts[0]
    elif len(parts) == 2:
        # Could be namespace/repository or registry/repository
        if "." in parts[0] or ":" in parts[0]:
            # Likely a registry (registry.io:5000/repo or registry.io/repo)
            registry_host, registry_port = parse_registry(parts[0])
            repository = parts[1]
        else:
            # Likely namespace/repository
            namespace = parts[0]
            repository = parts[1]
    elif len(parts) >= 3:
        # registry/namespace/repository or registry/nested/namespace/repository
        registry_host, registry_port = parse_registry(parts[0])
        namespace = "/".join(parts[1:-1])
        repository = parts[-1]

    # Validate that we found a repository
    if not repository:
        raise ValueError(f"Invalid image reference: no repository found in '{image}'")

    # Default tag to 'latest' if neither tag nor digest specified. This is Docker's default behavior.
    if tag is None and digest is None:
        tag = "latest"

    return ImageReference(
        repository=repository,
        namespace=namespace,
        tag=tag,
        digest=digest,
        registry_host=registry_host,
        registry_port=registry_port,
    )


@dataclass
class ContainerSpec:
    image: str = ""
    ports: list[str] = field(default_factory=list)
    networks: list[str] = field(default_factory=list)
    volumes: list[str] = field(default_factory=list)
    env_vars: list[str] = field(default_factory=list)
    pull_always: bool = False

    def container_create_args(self):
        args = []
        for network in self.networks:
            args.append("--network {0}".format(network))

        for port in self.ports:
            args.append("-p {0}".format(port))

        for volume in self.volumes:
            args.append("-v {0}".format(volume))

        for env_var in self.env_vars:
            args.append("-e {0}".format(env_var))

        if self.pull_always:
            args.append("--pull always")

        args.append(self.image)

        return args

    def diff_from_inspect(self, inspect_dict: dict[str, Any]) -> list[str]:
        # TODO(@minor-fixes): Diff output of "docker inspect" against this spec
        # to determine if the container needs to be recreated. Currently, this
        # function will never recreate when attributes change, which is
        # consistent with prior behavior.
        del inspect_dict
        return []


def _create_container(**kwargs):
    if "spec" not in kwargs:
        raise OperationError("missing 1 required argument: 'spec'")

    spec = kwargs["spec"]

    if not spec.image:
        raise OperationError("Docker image not specified")

    command = [
        "docker container create --name {0}".format(kwargs["container"])
    ] + spec.container_create_args()

    return " ".join(command)


def _remove_container(**kwargs):
    return "docker container rm -f {0}".format(kwargs["container"])


def _start_container(**kwargs):
    return "docker container start {0}".format(kwargs["container"])


def _stop_container(**kwargs):
    return "docker container stop {0}".format(kwargs["container"])


def _pull_image(**kwargs):
    return "docker image pull {0}".format(kwargs["image"])


def _remove_image(**kwargs):
    return "docker image rm {0}".format(kwargs["image"])


def _prune_command(**kwargs):
    command = ["docker system prune"]

    if kwargs["all"]:
        command.append("-a")

    if kwargs["filter"] != "":
        command.append("--filter={0}".format(kwargs["filter"]))

    if kwargs["volumes"]:
        command.append("--volumes")

    command.append("-f")

    return " ".join(command)


def _create_volume(**kwargs):
    command = []
    labels = kwargs["labels"] if kwargs["labels"] else []

    command.append("docker volume create {0}".format(kwargs["volume"]))

    if kwargs["driver"] != "":
        command.append("-d {0}".format(kwargs["driver"]))

    for label in labels:
        command.append("--label {0}".format(label))

    return " ".join(command)


def _remove_volume(**kwargs):
    return "docker image rm {0}".format(kwargs["volume"])


def _create_network(**kwargs):
    command = []
    aux_addresses = kwargs["aux_addresses"] if kwargs["aux_addresses"] else {}
    opts = kwargs["opts"] if kwargs["opts"] else []
    ipam_opts = kwargs["ipam_opts"] if kwargs["ipam_opts"] else []
    labels = kwargs["labels"] if kwargs["labels"] else []

    command.append("docker network create {0}".format(kwargs["network"]))
    if kwargs["driver"] != "":
        command.append("-d {0}".format(kwargs["driver"]))

    if kwargs["gateway"] != "":
        command.append("--gateway {0}".format(kwargs["gateway"]))

    if kwargs["ip_range"] != "":
        command.append("--ip-range {0}".format(kwargs["ip_range"]))

    if kwargs["ipam_driver"] != "":
        command.append("--ipam-driver {0}".format(kwargs["ipam_driver"]))

    if kwargs["subnet"] != "":
        command.append("--subnet {0}".format(kwargs["subnet"]))

    if kwargs["scope"] != "":
        command.append("--scope {0}".format(kwargs["scope"]))

    if kwargs["ingress"]:
        command.append("--ingress")

    if kwargs["attachable"]:
        command.append("--attachable")

    for host, address in aux_addresses.items():
        command.append("--aux-address '{0}={1}'".format(host, address))

    for opt in opts:
        command.append("--opt {0}".format(opt))

    for opt in ipam_opts:
        command.append("--ipam-opt {0}".format(opt))

    for label in labels:
        command.append("--label {0}".format(label))
    return " ".join(command)


def _remove_network(**kwargs):
    return "docker network rm {0}".format(kwargs["network"])


def _install_plugin(**kwargs):
    command = ["docker plugin install {0} --grant-all-permissions".format(kwargs["plugin"])]

    plugin_options = kwargs["plugin_options"] if kwargs["plugin_options"] else {}

    if kwargs["alias"]:
        command.append("--alias {0}".format(kwargs["alias"]))

    if not kwargs["enabled"]:
        command.append("--disable")

    for option, value in plugin_options.items():
        command.append("{0}={1}".format(option, value))

    return " ".join(command)


def _remove_plugin(**kwargs):
    return "docker plugin rm -f {0}".format(kwargs["plugin"])


def _enable_plugin(**kwargs):
    return "docker plugin enable {0}".format(kwargs["plugin"])


def _disable_plugin(**kwargs):
    return "docker plugin disable {0}".format(kwargs["plugin"])


def _set_plugin_options(**kwargs):
    command = ["docker plugin set {0}".format(kwargs["plugin"])]
    existent_options = kwargs.get("existing_options", {})
    required_options = kwargs.get("required_options", {})
    options_to_set = existent_options | required_options
    for option, value in options_to_set.items():
        command.append("{0}={1}".format(option, value))
    return " ".join(command)


def handle_docker(resource: str, command: str, **kwargs):
    container_commands = {
        "create": _create_container,
        "remove": _remove_container,
        "start": _start_container,
        "stop": _stop_container,
    }

    image_commands = {
        "pull": _pull_image,
        "remove": _remove_image,
    }

    volume_commands = {
        "create": _create_volume,
        "remove": _remove_volume,
    }

    network_commands = {
        "create": _create_network,
        "remove": _remove_network,
    }

    system_commands = {
        "prune": _prune_command,
    }

    plugin_commands = {
        "install": _install_plugin,
        "remove": _remove_plugin,
        "enable": _enable_plugin,
        "disable": _disable_plugin,
        "set": _set_plugin_options,
    }

    docker_commands = {
        "container": container_commands,
        "image": image_commands,
        "volume": volume_commands,
        "network": network_commands,
        "system": system_commands,
        "plugin": plugin_commands,
    }

    return docker_commands[resource][command](**kwargs)
