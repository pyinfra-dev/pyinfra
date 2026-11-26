"""
Operations for managing Podman containers, images, volumes, networks, plugins,
and registry authentication.

These operations are thin proxies around the equivalent Docker operations,
routing all commands through the ``podman`` CLI instead of ``docker``.

"""

from __future__ import annotations

from typing import Any

from pyinfra.api import operation
from pyinfra.operations import docker


@operation()
def container(*args: Any, **kwargs: Any):
    """
    Manage Podman containers.

    This is a proxy around :func:`pyinfra.operations.docker.container` that
    routes all commands through ``podman`` instead of ``docker``.
    """
    kwargs["docker_cmd"] = "podman"
    yield from docker.container._inner(*args, **kwargs)


@operation()
def image(*args: Any, **kwargs: Any):
    """
    Manage Podman images.

    This is a proxy around :func:`pyinfra.operations.docker.image` that
    routes all commands through ``podman`` instead of ``docker``.
    """
    kwargs["docker_cmd"] = "podman"
    yield from docker.image._inner(*args, **kwargs)


@operation()
def build(*args: Any, **kwargs: Any):
    """
    Build a Podman image from a Dockerfile.

    This is a proxy around :func:`pyinfra.operations.docker.build` that
    routes all commands through ``podman`` instead of ``docker``.
    """
    kwargs["docker_cmd"] = "podman"
    yield from docker.build._inner(*args, **kwargs)


@operation()
def volume(*args: Any, **kwargs: Any):
    """
    Manage Podman volumes.

    This is a proxy around :func:`pyinfra.operations.docker.volume` that
    routes all commands through ``podman`` instead of ``docker``.
    """
    kwargs["docker_cmd"] = "podman"
    yield from docker.volume._inner(*args, **kwargs)


@operation()
def network(*args: Any, **kwargs: Any):
    """
    Manage Podman networks.

    This is a proxy around :func:`pyinfra.operations.docker.network` that
    routes all commands through ``podman`` instead of ``docker``.
    """
    kwargs["docker_cmd"] = "podman"
    yield from docker.network._inner(*args, **kwargs)


@operation()
def prune(*args: Any, **kwargs: Any):
    """
    Prune unused Podman resources.

    This is a proxy around :func:`pyinfra.operations.docker.prune` that
    routes all commands through ``podman`` instead of ``docker``.
    """
    kwargs["docker_cmd"] = "podman"
    yield from docker.prune._inner(*args, **kwargs)


@operation()
def plugin(*args: Any, **kwargs: Any):
    """
    Manage Podman plugins.

    This is a proxy around :func:`pyinfra.operations.docker.plugin` that
    routes all commands through ``podman`` instead of ``docker``.
    """
    kwargs["docker_cmd"] = "podman"
    yield from docker.plugin._inner(*args, **kwargs)


@operation()
def login(*args: Any, **kwargs: Any):
    """
    Log in to a Podman registry.

    This is a proxy around :func:`pyinfra.operations.docker.login` that
    routes all commands through ``podman`` instead of ``docker``.
    """
    kwargs["docker_cmd"] = "podman"
    yield from docker.login._inner(*args, **kwargs)


@operation()
def logout(*args: Any, **kwargs: Any):
    """
    Log out of a Podman registry.

    This is a proxy around :func:`pyinfra.operations.docker.logout` that
    routes all commands through ``podman`` instead of ``docker``.
    """
    kwargs["docker_cmd"] = "podman"
    yield from docker.logout._inner(*args, **kwargs)


@operation()
def compose(*args: Any, **kwargs: Any):
    """
    Deploy a Podman Compose stack on the target.

    This is a proxy around :func:`pyinfra.operations.docker.compose` that
    routes all commands through ``podman compose`` instead of ``docker compose``.
    """
    kwargs["compose_command"] = "podman compose"
    yield from docker.compose._inner(*args, **kwargs)
