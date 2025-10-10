from __future__ import annotations

from typing_extensions import override

from .ssh_common import SSHCommonConnector


class AsyncSSHConnector(SSHCommonConnector):
    handles_execution = True

    @override
    @staticmethod
    def make_names_data(name):
        yield f"@async-ssh/{name}", {"ssh_hostname": name}, []
