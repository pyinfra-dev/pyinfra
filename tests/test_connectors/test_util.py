# encoding: utf-8

from unittest import TestCase

from pyinfra.api import Config, State
from pyinfra.connectors.util import (
    make_unix_command,
    make_unix_command_for_host,
    split_combined_output,
)

from ..util import make_inventory


class TestConnectorUtil(TestCase):
    def test_split_combined_output_works(self):
        results = split_combined_output(
            [
                ("stdout", "stdout1"),
                ("stdout", "stdout2"),
                ("stderr", "stderr1"),
                ("stdout", "stdout3"),
            ],
        )

        assert results == (["stdout1", "stdout2", "stdout3"], ["stderr1"])

    def test_split_combined_output_raises(self):
        with self.assertRaises(ValueError):
            split_combined_output(["nope", ""])


class TestMakeUnixCommandConnectorUtil(TestCase):
    def test_command(self):
        command = make_unix_command("echo Šablony")
        assert command.get_raw_value() == "sh -c 'echo Šablony'"

    def test_doas_command(self):
        command = make_unix_command("uptime", doas=True)
        assert command.get_raw_value() == "doas -n sh -c uptime"

    def test_doas_user_command(self):
        command = make_unix_command("uptime", doas=True, doas_user="pyinfra")
        assert command.get_raw_value() == "doas -n -u pyinfra sh -c uptime"

    def test_sudo_command(self):
        command = make_unix_command("uptime", sudo=True)
        assert command.get_raw_value() == "sudo -H -n sh -c uptime"

    def test_sudo_multi_arg_command(self):
        command = make_unix_command("echo hi", sudo=True, preserve_sudo_env=True)
        assert command.get_raw_value() == "sudo -H -n -E sh -c 'echo hi'"

    def test_sudo_preserve_env_command(self):
        command = make_unix_command("uptime", sudo=True, preserve_sudo_env=True)
        assert command.get_raw_value() == "sudo -H -n -E sh -c uptime"

    def test_use_sudo_login_command(self):
        command = make_unix_command("uptime", sudo=True, use_sudo_login=True)
        assert command.get_raw_value() == "sudo -H -n -i sh -c uptime"

    def test_sudo_user_command(self):
        command = make_unix_command("uptime", sudo=True, sudo_user="pyinfra")
        assert command.get_raw_value() == "sudo -H -n -u pyinfra sh -c uptime"

    def test_su_command(self):
        command = make_unix_command("uptime", su_user="pyinfra")
        assert command.get_raw_value() == "su pyinfra -c 'sh -c uptime'"

    def test_su_multi_arg_command(self):
        command = make_unix_command("echo hi", su_user="pyinfra")
        assert command.get_raw_value() == "su pyinfra -c 'sh -c '\"'\"'echo hi'\"'\"''"

    def test_use_su_login_command(self):
        command = make_unix_command("uptime", su_user="pyinfra", use_su_login=True)
        assert command.get_raw_value() == "su -l pyinfra -c 'sh -c uptime'"

    def test_preserve_su_env_command(self):
        command = make_unix_command("uptime", su_user="pyinfra", preserve_su_env=True)
        assert command.get_raw_value() == "su -m pyinfra -c 'sh -c uptime'"

    def test_su_shell_command(self):
        command = make_unix_command("uptime", su_user="pyinfra", su_shell="bash")
        assert command.get_raw_value() == "su -s `which bash` pyinfra -c 'sh -c uptime'"

    def test_command_env(self):
        command = make_unix_command(
            "uptime",
            env={
                "key": "value",
                "anotherkey": "anothervalue",
            },
        )
        assert command.get_raw_value() in [
            'sh -c \'export "key=value" "anotherkey=anothervalue" && uptime\'',
            'sh -c \'export "anotherkey=anothervalue" "key=value" && uptime\'',
        ]

    def test_command_chdir(self):
        command = make_unix_command("uptime", chdir="/opt/somedir")
        assert command.get_raw_value() == "sh -c 'cd /opt/somedir && uptime'"

    def test_custom_shell_command(self):
        command = make_unix_command("uptime", shell_executable="bash")
        assert command.get_raw_value() == "bash -c uptime"

    def test_mixed_command(self):
        command = make_unix_command(
            "echo hi",
            chdir="/opt/somedir",
            env={"key": "value"},
            sudo=True,
            sudo_user="root",
            preserve_sudo_env=True,
            su_user="pyinfra",
            shell_executable="bash",
        )
        assert command.get_raw_value() == (
            "sudo -H -n -E -u root "  # sudo bit
            "su pyinfra -c "  # su bit
            "'bash -c '\"'\"'cd /opt/somedir && export \"key=value\" "  # shell and export bit
            "&& echo hi'\"'\"''"  # command bit
        )

    def test_command_exists_su_config_only(self):
        """
        This tests covers a bug that appeared when `make_unix_command` is called
        with `su_user=False` (default) but `SU_USER` set on the config object,
        resulting in an empty command output.
        """
        state = State(make_inventory(), Config(SU_USER=True))
        host = state.inventory.get_host("somehost")
        command = make_unix_command_for_host(state, host, "echo Šablony")
        assert command.get_raw_value() == "sh -c 'echo Šablony'"
