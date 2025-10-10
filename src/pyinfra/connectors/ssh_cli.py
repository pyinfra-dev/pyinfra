from __future__ import annotations

from typing_extensions import override

from .ssh_common import SSHCommonConnector


class SSHCLIConnector(SSHCommonConnector):
    handles_execution = True

    @override
    @staticmethod
    def make_names_data(name):
        yield f"@ssh-cli/{name}", {"ssh_hostname": name}, []

    def __init__(self, state, host):
        super().__init__(state, host)
        self._use_ssh_cli = True
