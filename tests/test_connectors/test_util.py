from unittest import TestCase
from unittest.mock import MagicMock, patch

from pyinfra.api import Config, State, HiddenValue
from pyinfra.connectors.util import (
    CommandOutput,
    OutputLine,
    _ensure_askpass_set_for_host,
    make_unix_command,
    make_unix_command_for_host,
    remove_any_sudo_askpass_file,
)

from ..util import make_inventory


class TestMakeUnixCommandConnectorUtil(TestCase):
    def test_command(self):
        command = make_unix_command("echo Šablony")
        assert command.get_raw_value() == "sh -c 'echo Šablony'"

    def test_doas_command(self):
        command = make_unix_command("uptime", _doas=True)
        assert command.get_raw_value() == "doas -n sh -c uptime"

    def test_doas_user_command(self):
        command = make_unix_command("uptime", _doas=True, _doas_user="pyinfra")
        assert command.get_raw_value() == "doas -n -u pyinfra sh -c uptime"

    def test_doas_user_command_with_injection_attempt(self):
        command = make_unix_command("uptime", _doas=True, _doas_user="root; rm -rf /")
        assert command.get_raw_value() == ("doas -n -u 'root; rm -rf /' sh -c uptime")

    def test_dzdo_command(self):
        command = make_unix_command("uptime", _dzdo=True)
        assert command.get_raw_value() == "dzdo -H -n sh -c uptime"

    def test_dzdo_user_command(self):
        command = make_unix_command("uptime", _dzdo=True, _dzdo_user="pyinfra")
        assert command.get_raw_value() == "dzdo -H -n -u pyinfra sh -c uptime"

    def test_dzdo_user_command_with_injection_attempt(self):
        command = make_unix_command("uptime", _dzdo=True, _dzdo_user="root`id`")
        assert command.get_raw_value() == ("dzdo -H -n -u 'root`id`' sh -c uptime")

    def test_sudo_command(self):
        command = make_unix_command("uptime", _sudo=True)
        assert command.get_raw_value() == "sudo -H -n sh -c uptime"

    def test_sudo_multi_arg_command(self):
        command = make_unix_command("echo hi", _sudo=True, _preserve_sudo_env=True)
        assert command.get_raw_value() == "sudo -H -n -E sh -c 'echo hi'"

    def test_sudo_preserve_env_command(self):
        command = make_unix_command("uptime", _sudo=True, _preserve_sudo_env=True)
        assert command.get_raw_value() == "sudo -H -n -E sh -c uptime"

    def test_use_sudo_login_command(self):
        command = make_unix_command("uptime", _sudo=True, _use_sudo_login=True)
        assert command.get_raw_value() == "sudo -H -n -i sh -c uptime"

    def test_sudo_user_command(self):
        command = make_unix_command("uptime", _sudo=True, _sudo_user="pyinfra")
        assert command.get_raw_value() == "sudo -H -n -u pyinfra sh -c uptime"

    def test_sudo_user_command_with_injection_attempt(self):
        command = make_unix_command("uptime", _sudo=True, _sudo_user="root; touch /tmp/pwn")
        assert command.get_raw_value() == ("sudo -H -n -u 'root; touch /tmp/pwn' sh -c uptime")

    def test_sudo_password_askpass_path_quoted(self):
        command = make_unix_command(
            "uptime",
            _sudo=True,
            _sudo_password="secret",
            _sudo_askpass_path="/tmp/weird path; id",
        )
        # The askpass path contains shell metacharacters and must be quoted
        # so it cannot inject commands into the SUDO_ASKPASS env assignment.
        assert "SUDO_ASKPASS='/tmp/weird path; id'" in command.get_raw_value()

    def test_su_command(self):
        command = make_unix_command("uptime", _su_user="pyinfra")
        assert command.get_raw_value() == "su pyinfra -c 'sh -c uptime'"

    def test_su_command_with_injection_attempt(self):
        command = make_unix_command("uptime", _su_user="root$(id)")
        assert command.get_raw_value() == ("su 'root$(id)' -c 'sh -c uptime'")

    def test_su_multi_arg_command(self):
        command = make_unix_command("echo hi", _su_user="pyinfra")
        assert command.get_raw_value() == "su pyinfra -c 'sh -c '\"'\"'echo hi'\"'\"''"

    def test_use_su_login_command(self):
        command = make_unix_command("uptime", _su_user="pyinfra", _use_su_login=True)
        assert command.get_raw_value() == "su -l pyinfra -c 'sh -c uptime'"

    def test_preserve_su_env_command(self):
        command = make_unix_command("uptime", _su_user="pyinfra", _preserve_su_env=True)
        assert command.get_raw_value() == "su -m pyinfra -c 'sh -c uptime'"

    def test_su_shell_command(self):
        command = make_unix_command("uptime", _su_user="pyinfra", _su_shell="bash")
        assert command.get_raw_value() == "su -s $(command -v bash) pyinfra -c 'sh -c uptime'"

    def test_su_shell_command_with_injection_attempt(self):
        command = make_unix_command("uptime", _su_user="pyinfra", _su_shell="bash$(id)")
        # The injected `$(id)` must be safely quoted as a literal argument to
        # `command -v` rather than executed as a subshell.
        assert (
            command.get_raw_value() == "su -s $(command -v 'bash$(id)') pyinfra -c 'sh -c uptime'"
        )

    def test_su_password_command(self):
        command = make_unix_command(
            "uptime",
            _su_user="pyinfra",
            _su_password="mypassword",
            _su_askpass_path="/tmp/pyinfra-su-askpass-XXXX",
        )
        assert command.get_raw_value() == (
            "env PYINFRA_SU_PASSWORD=mypassword /tmp/pyinfra-su-askpass-XXXX "
            "| su pyinfra -c 'sh -c uptime'"
        )

    def test_command_env(self):
        command = make_unix_command(
            "uptime",
            _env={
                "key": "value",
                "anotherkey": "anothervalue",
            },
        )
        assert command.get_raw_value() in [
            "sh -c 'export key=value anotherkey=anothervalue && uptime'",
            "sh -c 'export anotherkey=anothervalue key=value && uptime'",
        ]

    def test_command_env_injection_attempt(self):
        command = make_unix_command(
            "uptime",
            _env={"KEY": 'value"; id; echo "'},
        )
        # The value contains shell metacharacters; it must be quoted as a
        # single literal token so it cannot inject additional commands.
        assert (
            command.get_raw_value()
            == "sh -c 'export '\"'\"'KEY=value\"; id; echo \"'\"'\"' && uptime'"
        )

    def test_command_env_hidden_value(self):
        command = make_unix_command(
            "uptime",
            _env={
                "KEY": HiddenValue("super-secret"),
            },
        )

        raw = command.get_raw_value()
        masked = command.get_masked_value()
        assert "super-secret" in raw
        assert "super-secret" not in masked
        assert "*MASKED*" in masked
        assert "KEY=*MASKED*" in masked

    def test_command_env_hidden_value_with_shell_chars(self):
        command = make_unix_command(
            "uptime",
            _env={
                "KEY": HiddenValue("abc; id; echo bad"),
            },
        )

        raw = command.get_raw_value()
        masked = command.get_masked_value()

        assert "abc; id; echo bad" in raw
        assert "abc; id; echo bad" not in masked
        assert "*MASKED*" in masked
        assert "KEY=*MASKED*" in masked

        # The raw command should still quote the assignment as one shell token.
        assert "'\"'\"'KEY=abc; id; echo bad'\"'\"'" in raw

    def test_command_chdir(self):
        command = make_unix_command("uptime", _chdir="/opt/somedir")
        assert command.get_raw_value() == "sh -c 'cd /opt/somedir && uptime'"

    def test_command_chdir_injection_attempt(self):
        command = make_unix_command("uptime", _chdir="/tmp; rm -rf / #")
        assert command.get_raw_value() == ("sh -c 'cd '\"'\"'/tmp; rm -rf / #'\"'\"' && uptime'")

    def test_custom_shell_command(self):
        command = make_unix_command("uptime", _shell_executable="bash")
        assert command.get_raw_value() == "bash -c uptime"

    def test_mixed_command(self):
        command = make_unix_command(
            "echo hi",
            _chdir="/opt/somedir",
            _env={"key": "value"},
            _sudo=True,
            _sudo_user="root",
            _preserve_sudo_env=True,
            _su_user="pyinfra",
            _shell_executable="bash",
        )
        assert command.get_raw_value() == (
            "sudo -H -n -E -u root "  # sudo bit
            "su pyinfra -c "  # su bit
            "'bash -c '\"'\"'cd /opt/somedir && export key=value "  # shell and export bit
            "&& echo hi'\"'\"''"  # command bit
        )

    def test_mixed_command_with_injection_attempts(self):
        command = make_unix_command(
            "echo hi",
            _chdir="/tmp; id",
            _env={"K": "v; id"},
            _sudo=True,
            _sudo_user="root$(id)",
            _su_user="pyinfra`id`",
            _su_shell="bash$(id)",
        )
        raw = command.get_raw_value()
        # None of the injected strings should appear unquoted. Every one of
        # them must be inside single-quotes somewhere in the output.
        assert "'root$(id)'" in raw
        assert "'pyinfra`id`'" in raw
        assert "'bash$(id)'" in raw
        # The chdir and env are embedded inside a nested sh -c, so check for
        # the escaped-single-quote form that shlex.quote produces.
        assert "/tmp; id" in raw
        assert "K=v; id" in raw
        # And the inner commands should survive through the layers of quoting.
        assert raw.endswith("'\"'\"''")

    def test_remove_any_sudo_askpass_file_quotes_path(self):
        commands = []

        host = MagicMock()
        host.connector_data = {
            "sudo_askpass_path__/tmp": "/tmp/weird path; id",
        }
        host.run_shell_command = lambda cmd: commands.append(cmd.get_raw_value())

        remove_any_sudo_askpass_file(host)

        assert commands == ["rm -f '/tmp/weird path; id'"]
        assert host.connector_data["sudo_askpass_path__/tmp"] is None

    def test_command_exists_su_config_only(self):
        """
        This tests covers a bug that appeared when `make_unix_command` is called
        with `_su_user=False` (default) but `SU_USER` set on the config object,
        resulting in an empty command output.
        """
        state = State(make_inventory(), Config(SU_USER=True))
        host = state.inventory.get_host("somehost")
        command = make_unix_command_for_host(state, host, "echo Šablony")
        assert command.get_raw_value() == "sh -c 'echo Šablony'"


class TestRemoveAnySudoAskpassFile(TestCase):
    def test_clears_state_and_runs_rm(self):
        commands = []
        host = MagicMock()
        host.connector_data = {
            "sudo_askpass_path__/tmp": "/tmp/sudo-askpass",
            "su_askpass_path__/tmp": "/tmp/su-askpass",
        }
        host.run_shell_command = lambda cmd: commands.append(cmd.get_raw_value())

        remove_any_sudo_askpass_file(host)

        assert sorted(commands) == [
            "rm -f /tmp/su-askpass",
            "rm -f /tmp/sudo-askpass",
        ]
        assert host.connector_data["sudo_askpass_path__/tmp"] is None
        assert host.connector_data["su_askpass_path__/tmp"] is None

    def test_clears_multiple_temp_dir_variants(self):
        commands = []
        host = MagicMock()
        host.connector_data = {
            "sudo_askpass_path__/tmp": "/tmp/sudo-askpass",
            "sudo_askpass_path__/var/tmp": "/var/tmp/sudo-askpass",
            "su_askpass_path__/dev/shm": "/dev/shm/su-askpass",
        }
        host.run_shell_command = lambda cmd: commands.append(cmd.get_raw_value())

        remove_any_sudo_askpass_file(host)

        assert sorted(commands) == [
            "rm -f /dev/shm/su-askpass",
            "rm -f /tmp/sudo-askpass",
            "rm -f /var/tmp/sudo-askpass",
        ]
        assert host.connector_data["sudo_askpass_path__/tmp"] is None
        assert host.connector_data["sudo_askpass_path__/var/tmp"] is None
        assert host.connector_data["su_askpass_path__/dev/shm"] is None

    def test_swallows_errors_and_clears_state(self):
        """
        Regression test for #1645: `host.disconnect()` -> `remove_any_sudo_askpass_file`
        is called after ``server.reboot`` when the SSH session is already dead.
        The remote ``rm`` must fail gracefully and the stored path must still
        be cleared so a reconnect will regenerate a fresh askpass file.
        """
        host = MagicMock()
        host.connector_data = {
            "sudo_askpass_path__/tmp": "/tmp/sudo-askpass",
            "su_askpass_path__/tmp": "/tmp/su-askpass",
        }

        def failing_run(cmd):
            raise Exception("SSH session not active")

        host.run_shell_command = failing_run

        # Must not raise, this is a best-effort cleanup.
        remove_any_sudo_askpass_file(host)

        assert host.connector_data["sudo_askpass_path__/tmp"] is None
        assert host.connector_data["su_askpass_path__/tmp"] is None

    def test_noop_when_no_state(self):
        host = MagicMock()
        host.connector_data = {
            "sudo_askpass_path__/tmp": None,
            "su_askpass_path__/tmp": None,
        }
        host.run_shell_command = MagicMock()

        remove_any_sudo_askpass_file(host)

        host.run_shell_command.assert_not_called()


class TestEnsureAskpassTempDir(TestCase):
    """
    The askpass helper must honour the resolved temp directory (issue #1623):
    operation-level ``_temp_dir`` > ``config.TEMP_DIR`` > ``config.DEFAULT_TEMP_DIR``.
    Per-host defaults for ``_temp_dir`` come through the standard global-argument
    cascade (``host.data._temp_dir``), not via a separate code path here.
    """

    _counter = 0

    @classmethod
    def _next_host(cls):
        cls._counter += 1
        return f"askpass-temp-dir-test-host-{cls._counter}"

    def _make_host(self, config=None):
        name = self._next_host()
        state = State(make_inventory(hosts=(name,)), config or Config())
        host = state.inventory.get_host(name)
        host.init(state)
        return host

    def _captured_script_run(self, host, temp_dir=None, stdout="/some/askpass/path"):
        """
        Call ``_ensure_askpass_set_for_host`` with ``host.run_shell_command``
        patched so we can assert on the remote script text (whose first
        argument to the mkstemp template is the temp directory).
        """
        captured = {}

        def fake_run(command, *args, **kwargs):
            captured["command"] = command
            return (True, CommandOutput([OutputLine("stdout", stdout)]))

        host.run_shell_command = fake_run  # type: ignore[method-assign]
        _ensure_askpass_set_for_host(
            host,
            key="sudo_askpass_path",
            env_var="PYINFRA_SUDO_PASSWORD",
            temp_dir=temp_dir,
        )
        return captured["command"]

    def test_default_temp_dir(self):
        host = self._make_host()
        script = self._captured_script_run(host)
        assert "${TMPDIR:=/tmp}" in script

    def test_config_temp_dir(self):
        host = self._make_host(Config(TEMP_DIR="/var/tmp"))
        script = self._captured_script_run(host)
        assert "${TMPDIR:=/var/tmp}" in script

    def test_op_temp_dir_wins_over_config(self):
        host = self._make_host(Config(TEMP_DIR="/var/tmp"))
        script = self._captured_script_run(host, temp_dir="/dev/shm/pyinfra")
        assert "${TMPDIR:=/dev/shm/pyinfra}" in script

    def test_distinct_temp_dirs_get_distinct_cache_entries(self):
        host = self._make_host()
        first = self._captured_script_run(host, temp_dir="/a", stdout="/a/askpass")
        assert "${TMPDIR:=/a}" in first
        second = self._captured_script_run(host, temp_dir="/b", stdout="/b/askpass")
        assert "${TMPDIR:=/b}" in second
        assert host.connector_data["sudo_askpass_path__/a"] == "/a/askpass"
        assert host.connector_data["sudo_askpass_path__/b"] == "/b/askpass"

    def test_same_temp_dir_reuses_cache(self):
        host = self._make_host()
        calls = {"count": 0}

        def fake_run(command, *args, **kwargs):
            calls["count"] += 1
            return (True, CommandOutput([OutputLine("stdout", "/tmp/askpass-XYZ")]))

        host.run_shell_command = fake_run  # type: ignore[method-assign]

        first = _ensure_askpass_set_for_host(
            host,
            key="sudo_askpass_path",
            env_var="PYINFRA_SUDO_PASSWORD",
            temp_dir="/tmp",
        )
        second = _ensure_askpass_set_for_host(
            host,
            key="sudo_askpass_path",
            env_var="PYINFRA_SUDO_PASSWORD",
            temp_dir="/tmp",
        )

        assert first == second == "/tmp/askpass-XYZ"
        assert calls["count"] == 1

    def test_make_unix_command_for_host_threads_temp_dir(self):
        host = self._make_host()
        host.connector_data["prompted_sudo_password"] = "supersecret"

        captured = {}

        def fake_run(command, *args, **kwargs):
            captured["command"] = command
            return (
                True,
                CommandOutput([OutputLine("stdout", "/op/tmp/pyinfra-askpass-XYZ")]),
            )

        host.run_shell_command = fake_run  # type: ignore[method-assign]

        with patch("pyinfra.connectors.util.make_unix_command") as fake_make:
            fake_make.return_value = "mocked"
            make_unix_command_for_host(
                host.state,
                host,
                "uptime",
                _sudo=True,
                _sudo_password="supersecret",
                _temp_dir="/op/tmp",
            )

        assert "${TMPDIR:=/op/tmp}" in captured["command"]
