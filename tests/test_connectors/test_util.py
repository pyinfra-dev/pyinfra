# encoding: utf-8

from __future__ import unicode_literals

from unittest import TestCase

try:
    from pathlib import PurePosixPath
    HAS_PATHLIB = True
except ImportError:
    HAS_PATHLIB = False

from pyinfra.api.connectors.util import (
    escape_unix_path,
    make_unix_command,
    split_combined_output,
)


class TestConnectorUtil(TestCase):
    def test_split_combined_output_works(self):
        results = split_combined_output([
            ('stdout', 'stdout1'),
            ('stdout', 'stdout2'),
            ('stderr', 'stderr1'),
            ('stdout', 'stdout3'),
        ])

        assert results == (['stdout1', 'stdout2', 'stdout3'], ['stderr1'])

    def test_split_combined_output_raises(self):
        with self.assertRaises(ValueError):
            split_combined_output(['nope', ''])


class TestEscapeUnixPathUtil(TestCase):
    def test_path(self):
        escaped_path = escape_unix_path('/path/to/directory with space/ starts')
        assert escaped_path == '/path/to/directory\\ with\\ space/\\ starts'

    def test_escaped_path(self):
        escaped_path = '/path/to/directory\\ with\\ space/\\ starts'
        double_escaped_path = escape_unix_path(escaped_path)
        assert double_escaped_path == escaped_path

    def test_pathlib_path(self):
        if not HAS_PATHLIB:
            return

        path = PurePosixPath('/', 'path', 'to', 'directory with space', ' starts')
        escaped_path = escape_unix_path(path)
        assert escaped_path == '/path/to/directory\\ with\\ space/\\ starts'


class TestMakeUnixCommandConnectorUtil(TestCase):
    def test_command(self):
        command = make_unix_command('echo Šablony')
        assert command.get_raw_value() == "sh -c 'echo Šablony'"

    def test_sudo_command(self):
        command = make_unix_command('uptime', sudo=True)
        assert command.get_raw_value() == 'sudo -H -n sh -c uptime'

    def test_sudo_multi_arg_command(self):
        command = make_unix_command('echo hi', sudo=True, preserve_sudo_env=True)
        assert command.get_raw_value() == "sudo -H -n -E sh -c 'echo hi'"

    def test_sudo_preserve_env_command(self):
        command = make_unix_command('uptime', sudo=True, preserve_sudo_env=True)
        assert command.get_raw_value() == 'sudo -H -n -E sh -c uptime'

    def test_use_sudo_login_command(self):
        command = make_unix_command('uptime', sudo=True, use_sudo_login=True)
        assert command.get_raw_value() == 'sudo -H -n -i sh -c uptime'

    def test_sudo_user_command(self):
        command = make_unix_command('uptime', sudo=True, sudo_user='pyinfra')
        assert command.get_raw_value() == 'sudo -H -n -u pyinfra sh -c uptime'

    def test_su_command(self):
        command = make_unix_command('uptime', su_user='pyinfra')
        assert command.get_raw_value() == "su pyinfra -c 'sh -c uptime'"

    def test_su_multi_arg_command(self):
        command = make_unix_command('echo hi', su_user='pyinfra')
        assert command.get_raw_value() == "su pyinfra -c 'sh -c '\"'\"'echo hi'\"'\"''"

    def test_use_su_login_command(self):
        command = make_unix_command('uptime', su_user='pyinfra', use_su_login=True)
        assert command.get_raw_value() == "su -l pyinfra -c 'sh -c uptime'"

    def test_preserve_su_env_command(self):
        command = make_unix_command('uptime', su_user='pyinfra', preserve_su_env=True)
        assert command.get_raw_value() == "su -m pyinfra -c 'sh -c uptime'"

    def test_su_shell_command(self):
        command = make_unix_command('uptime', su_user='pyinfra', su_shell='bash')
        assert command.get_raw_value() == "su -s `which bash` pyinfra -c 'sh -c uptime'"

    def test_command_env(self):
        command = make_unix_command('uptime', env={
            'key': 'value',
            'anotherkey': 'anothervalue',
        })
        assert command.get_raw_value() in [
            "sh -c 'export key=value anotherkey=anothervalue && uptime'",
            "sh -c 'export anotherkey=anothervalue key=value && uptime'",
        ]

    def test_command_chdir(self):
        command = make_unix_command('uptime', chdir='/opt/somedir')
        assert command.get_raw_value() == "sh -c 'cd /opt/somedir && uptime'"

    def test_custom_shell_command(self):
        command = make_unix_command('uptime', shell_executable='bash')
        assert command.get_raw_value() == 'bash -c uptime'

    def test_mixed_command(self):
        command = make_unix_command(
            'echo hi',
            chdir='/opt/somedir',
            env={'key': 'value'},
            sudo=True,
            sudo_user='root',
            preserve_sudo_env=True,
            su_user='pyinfra',
            shell_executable='bash',
        )
        assert command.get_raw_value() == (
            'sudo -H -n -E -u root '  # sudo bit
            'su pyinfra -c '  # su bit
            "'bash -c '\"'\"'cd /opt/somedir && export key=value && echo hi'\"'\"''"  # command bit
        )
