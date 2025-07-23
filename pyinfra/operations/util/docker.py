import dataclasses
from typing import Any, Dict, List

from pyinfra.api import OperationError


@dataclasses.dataclass
class ContainerSpec:
    image: str = ""
    ports: List[str] = dataclasses.field(default_factory=list)
    networks: List[str] = dataclasses.field(default_factory=list)
    volumes: List[str] = dataclasses.field(default_factory=list)
    env_vars: List[str] = dataclasses.field(default_factory=list)
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

    def diff_from_inspect(self, inspect_dict: Dict[str, Any]) -> List[str]:
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


def handle_docker(resource, command, **kwargs):
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

    docker_commands = {
        "container": container_commands,
        "image": image_commands,
        "volume": volume_commands,
        "network": network_commands,
        "system": system_commands,
    }

    return docker_commands[resource][command](**kwargs)
