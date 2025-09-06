from __future__ import annotations

import json

from typing_extensions import override

from pyinfra.api import FactBase


class OpenvzContainers(FactBase):
    """
    Returns a dict of running OpenVZ containers by CTID:

    .. code:: python

        {
            666: {
                "ip": [],
                "ostemplate": "ubuntu...",
                ...
            },
        }
    """

    @override
    def command(self) -> str:
        return "vzlist -a -j"

    @override
    def requires_command(self) -> str:
        return "vzlist"

    default = dict

    @override
    def process(self, output):
        combined_json = "".join(output)
        vz_data = json.loads(combined_json)

        return {int(vz.pop("ctid")): vz for vz in vz_data}
