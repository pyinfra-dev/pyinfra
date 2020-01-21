from unittest import TestCase

from pyinfra.api.util import (
    format_exception,
    get_caller_frameinfo,
    make_command,
    try_int,
    underscore,
)


class TestApiUtil(TestCase):
    def test_try_int_number(self):
        self.assertEqual(try_int('1'), 1)

    def test_try_int_fail(self):
        self.assertEqual(try_int('hello'), 'hello')

    def test_get_caller_frameinfo(self):
        def _get_caller_frameinfo():
            return get_caller_frameinfo()

        frameinfo = _get_caller_frameinfo()
        self.assertEqual(frameinfo.lineno, 23)  # called by the line above

    def test_underscore(self):
        for camel_string, snake_string in (
            ('ThisIsHowYouDoIt', 'this_is_how_you_do_it'),
            ('This What_nope', 'this _what_nope'),
            ('myNameIs', 'my_name_is'),
        ):
            self.assertEqual(underscore(camel_string), snake_string)

    def test_format_exception(self):
        exception = Exception('I am a message', 1)
        self.assertEqual(
            format_exception(exception),
            "Exception('I am a message', 1)",
        )


class TestMakeCommandApiUtil(TestCase):
    def test_command(self):
        command = make_command('uptime')
        self.assertEqual(command, 'sh -c uptime')

    def test_sudo_command(self):
        command = make_command('uptime', sudo=True)
        self.assertEqual(command, 'sudo -S -H -n sh -c uptime')

    def test_sudo_preserve_env_command(self):
        command = make_command('uptime', sudo=True, preserve_sudo_env=True)
        self.assertEqual(command, 'sudo -S -H -n -E sh -c uptime')

    def test_use_sudo_login_command(self):
        command = make_command('uptime', sudo=True, use_sudo_login=True)
        self.assertEqual(command, 'sudo -S -H -n -i sh -c uptime')

    def test_sudo_user_command(self):
        command = make_command('uptime', sudo=True, sudo_user='pyinfra')
        self.assertEqual(command, 'sudo -S -H -n -u pyinfra sh -c uptime')

    def test_su_command(self):
        command = make_command('uptime', su_user='pyinfra')
        self.assertEqual(command, 'su pyinfra -s `which sh` -c uptime')

    def test_use_su_login_command(self):
        command = make_command('uptime', su_user='pyinfra', use_su_login=True)
        self.assertEqual(command, 'su -l pyinfra -s `which sh` -c uptime')

    def test_command_env(self):
        command = make_command('uptime', env={'key': 'value'})
        self.assertEqual(command, "sh -c 'export key=value; uptime'")

    def test_custom_shell_command(self):
        command = make_command('uptime', shell_executable='bash')
        self.assertEqual(command, 'bash -c uptime')

    def test_mixed_command(self):
        command = make_command(
            'uptime',
            env={'key': 'value'},
            sudo=True,
            sudo_user='root',
            preserve_sudo_env=True,
            su_user='pyinfra',
            shell_executable='bash',
        )
        self.assertEqual(
            command,
            (
                'sudo -S -H -n -E -u root '  # sudo bit
                'su pyinfra -s `which bash` -c '  # su bit
                "'export key=value; uptime'"  # command bit
            ),
        )
