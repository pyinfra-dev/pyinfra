from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, TypeVar

from pyinfra.api import FactBase

T = TypeVar("T")


class PodmanFactBase(FactBase[T]):
    """
    Base for facts using `podman` to retrieve
    """

    abstract = True

    def requires_command(self, *args, **kwargs) -> str:
        return "podman"


class PodmanSystemInfo(PodmanFactBase[Dict[str, Any]]):
    """
    Output of 'podman system info'
    """

    def command(self) -> str:
        return "podman system info --format=json"

    def process(self, output: Iterable[str]) -> Dict[str, Any]:
        output = json.loads(("").join(output))
        assert isinstance(output, dict)
        return output


class PodmanPs(PodmanFactBase[List[Dict[str, Any]]]):
    """
    Output of 'podman ps'
    """

    def command(self) -> str:
        return "podman ps --format=json --all"

    def process(self, output: Iterable[str]) -> List[Dict[str, Any]]:
        output = json.loads(("").join(output))
        assert isinstance(output, list)
        return output  # type: ignore
