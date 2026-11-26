from __future__ import annotations

import json

from typing_extensions import override

from pyinfra.api import ShellFact


class LxdContainers(ShellFact):
    """
    Returns a list of running LXD containers
    """

    @override
    def command(self) -> str:
        return "lxc list --format json --fast"

    @override
    def requires_command(self) -> str:
        return "lxc"

    default = list

    @override
    def process(self, output):
        output = list(output)
        assert len(output) == 1
        return json.loads(output[0])
