import json
from unittest import TestCase
from unittest.mock import mock_open, patch

from pyinfra.api.exceptions import InventoryError
from pyinfra.connectors.mech import get_mech_options, make_names_data

FAKE_MECH_OPTIONS = {
    "groups": {
        "ubuntu16": ["mygroup"],
    },
    "data": {
        "centos7": {
            "somedata": "somevalue",
        },
    },
}
FAKE_MECH_OPTIONS_DATA = json.dumps(FAKE_MECH_OPTIONS)


def fake_mech_shell(command, splitlines=None):
    if command == "mech ls":
        return [
            "NAME	        ADDRESS	                                BOX	     VERSION	PATH",  # noqa: E501
            "ubuntu16	       192.168.2.226             bento/ubuntu-16.04	 201912.04.0	/Users/bob/somedir/ubuntu16",  # noqa: E501
            "centos7	       192.168.2.227                 bento/centos-7	 201912.05.0	/Users/bob/somedir/centos7",  # noqa: E501
            "centos6	       poweroff                      bento/centos-6	 201912.04.0	/Users/bob/somedir/centos6",  # noqa: E501
            "fedora31	               	                    bento/fedora-31	 201912.04.0	/Users/bob/somedir/fedora31",  # noqa: E501
        ]
    if command == "mech ssh-config ubuntu16":
        return [
            "Host ubuntu16",
            "  User vagrant",
            "  Port 22",
            "  UserKnownHostsFile /dev/null",
            "  StrictHostKeyChecking no",
            "  PasswordAuthentication no",
            "  IdentityFile path/to/key",
            "  IdentitiesOnly yes",
            "  LogLevel FATAL",
            "  HostName 192.168.2.226",
            "",
        ]
    if command == "mech ssh-config centos7":
        return [
            "Host centos7",
            "  User vagrant",
            "  Port 22",
            "  UserKnownHostsFile /dev/null",
            "  StrictHostKeyChecking no",
            "  PasswordAuthentication no",
            "  IdentityFile path/to/key",
            "  IdentitiesOnly yes",
            "  LogLevel FATAL",
            "  HostName 192.168.2.227",
            "",
        ]
    if command == "mech ssh-config centos6":
        return [
            "ERROR: Error: The virtual machine is not powered on: /Users/bob/debian8/.mech/debian-8.11-amd64.vmx",  # noqa: E501
            "This Mech machine is reporting that it is not yet ready for SSH. Make",
            "sure your machine is created and running and try again. Additionally,",
            "check the output of `mech status` to verify that the machine is in the",
            "state that you expect.",
        ]

    return []


@patch("pyinfra.connectors.mech.local.shell", fake_mech_shell)
class TestMechConnector(TestCase):
    def tearDown(self):
        get_mech_options.cache = {}

    @patch(
        "pyinfra.connectors.mech.open",
        mock_open(read_data=FAKE_MECH_OPTIONS_DATA),
        create=True,
    )
    @patch("pyinfra.connectors.mech.path.exists", lambda path: True)
    def test_make_names_data_with_options(self):
        data = make_names_data()

        assert data == [
            (
                "@mech/ubuntu16",
                {
                    "ssh_port": "22",
                    "ssh_user": "vagrant",
                    "ssh_hostname": "192.168.2.226",
                    "ssh_key": "path/to/key",
                },
                ["mygroup", "@mech"],
            ),
            (
                "@mech/centos7",
                {
                    "ssh_port": "22",
                    "ssh_user": "vagrant",
                    "ssh_hostname": "192.168.2.227",
                    "ssh_key": "path/to/key",
                    "somedata": "somevalue",
                },
                ["@mech"],
            ),
        ]

    def test_make_names_data_with_limit(self):
        data = make_names_data(limit=("ubuntu16",))

        assert data == [
            (
                "@mech/ubuntu16",
                {
                    "ssh_port": "22",
                    "ssh_user": "vagrant",
                    "ssh_hostname": "192.168.2.226",
                    "ssh_key": "path/to/key",
                },
                ["@mech"],
            ),
        ]

    def test_make_names_data_no_matches(self):
        with self.assertRaises(InventoryError):
            make_names_data(limit="nope")
