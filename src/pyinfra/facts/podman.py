from __future__ import annotations

import json
from typing import Any, TypeVar
from collections.abc import Iterable
from typing_extensions import override

from pyinfra.api import FactBase
from pyinfra.api.exceptions import FactProcessError


T = TypeVar("T")
PodmanJsonT = TypeVar("PodmanJsonT", list, dict)


def _parse_podman_json(value: Iterable[str], expected: type[PodmanJsonT]) -> PodmanJsonT:
    """Parse podman output with `--format=json` option as JSON.

    Raises:
        FactProcessError: Exceptions captured during parsing are wrapped.
    """
    try:
        output = json.loads("".join(value))
    except Exception as e:
        raise FactProcessError(f"parse podman JSON output: {e}") from e
    if not isinstance(output, expected):
        raise FactProcessError(
            f"decode podman output: expected {expected.__name__}, got {type(output)}"
        )
    return output


class PodmanFactBase(FactBase[T]):
    """
    Base for facts using `podman` to retrieve
    """

    abstract = True

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "podman"


class PodmanSystemInfo(PodmanFactBase[dict[str, Any]]):
    """
    Output of 'podman system info'
    """

    @override
    def command(self) -> str:
        return "podman system info --format=json"

    @override
    def process(self, output: Iterable[str]) -> dict[str, Any]:
        output = json.loads(("").join(output))
        assert isinstance(output, dict)
        return output


class PodmanPs(PodmanFactBase[list[dict[str, Any]]]):
    """
    Output of 'podman ps'
    """

    @override
    def command(self) -> str:
        return "podman ps --format=json --all"

    @override
    def process(self, output: Iterable[str]) -> list[dict[str, Any]]:
        output = json.loads(("").join(output))
        assert isinstance(output, list)
        return output  # type: ignore


class PodmanImages(PodmanFactBase[list[dict[str, Any]]]):
    """Returns a list of all container images.
    This is equivalent to ``podman image ls --all``.

    .. code:: python

        [
            {
                "Id": "d529dd0c...",
                "ParentId": "",
                "RepoTags": null,
                "RepoDigests": [
                    "docker.io/library/alpine@sha256:28bd5fe8...",
                    "docker.io/library/alpine@sha256:79ff19e9..."
                ],
                "Size": 8709729,
                "SharedSize": 0,
                "VirtualSize": 8709729,
                "Labels": null,
                "Containers": 0,
                "Digest": "sha256:28bd5fe8...",
                "History": [
                    "docker.io/library/alpine:3.24",
                    "docker.io/library/alpine:latest"
                ],
                "Names": [
                    "docker.io/library/alpine:latest",
                    "docker.io/library/alpine:3.24"
                ],
                "Created": 1781568089,
                "CreatedAt": "2026-06-16T00:01:29Z"
            }
        ]
    """

    @override
    def command(self) -> str:
        return "podman image ls --format=json --all"

    @override
    def process(self, output: Iterable[str]) -> list[dict[str, Any]]:
        return _parse_podman_json(output, list)


class PodmanVolumes(PodmanFactBase[list[dict[str, Any]]]):
    """Returns a list of all volumes.
    This is equivalent to ``podman volume ls``.

    .. code:: python

        [
            {
                "Name": "postgres_data",
                "Driver": "local",
                "Mountpoint": "/home/user/.local/share/containers/storage/volumes/postgres_data/_data",
                "CreatedAt": "2026-05-07T20:13:33.435751494+02:00",
                "Labels": {
                    "com.docker.compose.project": "postgres",
                    "io.podman.compose.project": "postgres"
                },
                "Scope": "local",
                "Options": {},
                "MountCount": 0,
                "NeedsCopyUp": true,
                "LockNumber": 1
            }
        ]
    """

    @override
    def command(self) -> str:
        return "podman volume ls --format=json"

    @override
    def process(self, output: Iterable[str]) -> list[dict[str, Any]]:
        return _parse_podman_json(output, list)


class PodmanPods(PodmanFactBase[list[dict[str, Any]]]):
    """Returns a list of all pods.
    This is equivalent to ``podman pod ps``.

    .. code:: python

        [
            {
                "Cgroup": "user.slice",
                "Containers": [
                    {
                        "Id": "7787b95b...",
                        "Names": "qdrant",
                        "Status": "exited",
                        "RestartCount": 0
                    }
                ],
                "Created": "2026-05-08T14:29:50.634923891+02:00",
                "Id": "1c8e9eccf...",
                "InfraId": "",
                "Name": "pod_qdrant",
                "Namespace": "",
                "Networks": [],
                "Status": "Exited",
                "Labels": {}
            }
        ]
    """

    @override
    def command(self) -> str:
        return "podman pod ps --format=json"

    @override
    def process(self, output: Iterable[str]) -> list[dict[str, Any]]:
        return _parse_podman_json(output, list)


class PodmanQuadlets(PodmanFactBase[list[dict[str, Any]]]):
    """Returns a list of podman quadlets.
    This is equivalent to ``podman quadlet list``.

    **Note**: Available since Podman [v5.6.0][release_notes]. This version
    constraint is NOT checked automatically.

    [release_notes]: https://github.com/podman-container-tools/podman/releases/tag/v5.6.0

    .. code:: python

        [
            {
                "Name": "grafana-data.volume",
                "UnitName": "grafana-data-volume.service",
                "Path": "/home/user/.config/containers/systemd/grafana-data.volume",
                "Status": "active/exited",
                "App": ""
            },
            {
                "Name": "grafana.container",
                "UnitName": "grafana.service",
                "Path": "/home/user/.config/containers/systemd/grafana.container",
                "Status": "active/running",
                "App": ""
            }
        ]
    """

    @override
    def command(self) -> str:
        return "podman quadlet list --format=json"

    @override
    def process(self, output: Iterable[str]) -> list[dict[str, Any]]:
        return _parse_podman_json(output, list)


class PodmanNetworks(PodmanFactBase[list[dict[str, Any]]]):
    """Returns a list of all podman networks.
    This is equivalent to ``podman network ls``.

    .. code:: python

        [
            {
                "name": "podman",
                "id": "2f259bab...",
                "driver": "bridge",
                "network_interface": "podman0",
                "created": "2026-07-25T17:51:57.975124805+02:00",
                "subnets": [
                    {
                        "subnet": "10.88.0.0/16",
                        "gateway": "10.88.0.1"
                    }
                ],
                "ipv6_enabled": false,
                "internal": false,
                "dns_enabled": false,
                "ipam_options": {
                    "driver": "host-local"
                }
            }
        ]
    """

    @override
    def command(self) -> str:
        return "podman network ls --format=json"

    @override
    def process(self, output: Iterable[str]) -> list[dict[str, Any]]:
        return _parse_podman_json(output, list)
