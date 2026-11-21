import json
import shlex
from io import BytesIO
from subprocess import PIPE
from unittest import TestCase
from unittest.mock import mock_open, patch

from pyinfra.api import Config, State
from pyinfra.api.exceptions import ConnectError, InventoryError, PyinfraError
from pyinfra.connectors.incus import IncusConnector, LXCConnector
from pyinfra.connectors.util import make_unix_command

from ..util import make_inventory

INSTANCES = [
    {"name": "container-one", "status": "Running", "type": "container", "project": "default"},
    {"name": "vm-one", "status": "Running", "type": "virtual-machine", "project": "default"},
    {"name": "stopped-one", "status": "Stopped", "type": "container", "project": "default"},
]
REMOTE_INSTANCES = [
    {"name": "remote-one", "status": "Running", "type": "container", "project": "default"},
]


def fake_incus_shell(command, splitlines=None):
    if command == "incus list --all-projects --format json --fast":
        return json.dumps(INSTANCES)
    if command == "incus list remote: --all-projects --format json --fast":
        return json.dumps(REMOTE_INSTANCES)
    if command == "lxc list --all-projects --format json --fast":
        return json.dumps(INSTANCES)
    raise PyinfraError(f"Invalid command: {command}")


def make_instance_data(name, instance_type, remote=None, project="default"):
    data = {
        "incus_name": name,
        "incus_type": instance_type,
        "incus_project": project,
    }
    if remote is not None:
        data["incus_remote"] = remote
    return data


@patch("pyinfra.connectors.incus.local.shell", fake_incus_shell)
class TestIncusConnectorNamesData(TestCase):
    def test_all_running_instances(self):
        assert list(IncusConnector.make_names_data()) == [
            (
                "@incus/container-one",
                make_instance_data("container-one", "container"),
                ["@incus"],
            ),
            (
                "@incus/vm-one",
                make_instance_data("vm-one", "virtual-machine"),
                ["@incus"],
            ),
        ]

    def test_named_instance(self):
        assert list(IncusConnector.make_names_data("vm-one")) == [
            (
                "@incus/vm-one",
                make_instance_data("vm-one", "virtual-machine"),
                ["@incus"],
            ),
        ]

    def test_comma_separated_instances(self):
        hosts = list(IncusConnector.make_names_data("container-one, vm-one"))
        assert [host[0] for host in hosts] == ["@incus/container-one", "@incus/vm-one"]

    def test_remote_instances(self):
        assert list(IncusConnector.make_names_data("remote:")) == [
            (
                "@incus/remote:remote-one",
                make_instance_data("remote-one", "container", remote="remote"),
                ["@incus"],
            ),
        ]

    def test_remote_named_instance(self):
        hosts = list(IncusConnector.make_names_data("remote:remote-one"))
        assert hosts == [
            (
                "@incus/remote:remote-one",
                make_instance_data("remote-one", "container", remote="remote"),
                ["@incus"],
            ),
        ]

    def test_lxc_instance(self):
        assert list(LXCConnector.make_names_data("vm-one")) == [
            (
                "@lxc/vm-one",
                make_instance_data("vm-one", "virtual-machine"),
                ["@lxc"],
            ),
        ]

    def test_duplicate_instance_names_across_projects(self):
        instances = [
            {"name": "duplicate", "status": "Running", "type": "container", "project": "one"},
            {"name": "duplicate", "status": "Running", "type": "container", "project": "two"},
        ]
        with patch("pyinfra.connectors.incus.local.shell", return_value=json.dumps(instances)):
            with self.assertRaisesRegex(InventoryError, "Duplicate"):
                list(IncusConnector.make_names_data())

    def test_missing_project(self):
        instances = [{"name": "container-one", "status": "Running", "type": "container"}]
        with patch("pyinfra.connectors.incus.local.shell", return_value=json.dumps(instances)):
            with self.assertRaisesRegex(InventoryError, "no project information"):
                list(IncusConnector.make_names_data())

    def test_missing_instance(self):
        with self.assertRaisesRegex(InventoryError, "missing"):
            list(IncusConnector.make_names_data("missing"))

    def test_stopped_instance(self):
        with self.assertRaisesRegex(InventoryError, "stopped-one"):
            list(IncusConnector.make_names_data("stopped-one"))

    def test_empty_name(self):
        with self.assertRaisesRegex(InventoryError, "No Incus instance name"):
            list(IncusConnector.make_names_data(",,"))

    def test_no_running_instances(self):
        with patch("pyinfra.connectors.incus.local.shell", return_value="[]"):
            with self.assertRaisesRegex(InventoryError, "No running incus instances found"):
                list(IncusConnector.make_names_data())

    def test_invalid_json(self):
        with patch("pyinfra.connectors.incus.local.shell", return_value="not-json"):
            with self.assertRaisesRegex(InventoryError, "parse"):
                list(IncusConnector.make_names_data())

    def test_invalid_instance_entry(self):
        with patch("pyinfra.connectors.incus.local.shell", return_value="[{}]"):
            with self.assertRaisesRegex(InventoryError, "entry format"):
                list(IncusConnector.make_names_data())


@patch("pyinfra.connectors.incus.local.shell", fake_incus_shell)
@patch("pyinfra.connectors.incus.mkstemp", lambda: (None, "__tempfile__"))
@patch("pyinfra.connectors.incus.os.remove", lambda filename: None)
@patch("pyinfra.connectors.incus.os.close", lambda fd: None)
@patch("pyinfra.connectors.incus.open", mock_open(read_data=b"test!"), create=True)
@patch("pyinfra.api.util.open", mock_open(read_data=b"test!"), create=True)
class TestIncusConnector(TestCase):
    def setUp(self):
        self.fake_popen_patch = patch("pyinfra.connectors.util.Popen")
        self.fake_popen_mock = self.fake_popen_patch.start()
        self.fake_popen_mock().returncode = 0

    def tearDown(self):
        self.fake_popen_patch.stop()

    def make_host(self, name="container-one", connector="incus"):
        inventory = make_inventory(hosts=(f"@{connector}/{name}",))
        State(inventory, Config())
        return inventory.get_host(f"@{connector}/{name}")

    def test_connect(self):
        host = self.make_host("vm-one")
        host.connect()
        command = self.fake_popen_mock.call_args.args[0]
        assert "incus exec vm-one -- true" in command

    def test_connect_error(self):
        self.fake_popen_mock().returncode = 1
        host = self.make_host("vm-one")
        with self.assertRaisesRegex(ConnectError, "incus-agent"):
            host.connect(raise_exceptions=True)

    def test_run_shell_command(self):
        host = self.make_host()
        host.connect()
        self.fake_popen_mock.reset_mock()

        status, _ = host.run_shell_command(
            "echo hi",
            _stdin="hello",
            _get_pty=True,
            print_output=True,
        )
        assert status is True

        command = make_unix_command("echo hi").get_raw_value()
        command = shlex.quote(command)
        incus_command = f"incus exec --force-interactive container-one -- sh -c {command}"
        shell_command = make_unix_command(incus_command).get_raw_value()
        self.fake_popen_mock.assert_called_once_with(
            shell_command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    def test_run_shell_command_non_interactive(self):
        host = self.make_host()
        status, _ = host.run_shell_command("echo hi")
        assert status is True
        command = self.fake_popen_mock.call_args.args[0]
        assert "incus exec container-one" in command
        assert "--force-interactive" not in command

    def test_remote_run_shell_command(self):
        host = self.make_host("remote:remote-one")
        status, _ = host.run_shell_command("echo hi")
        assert status is True
        command = self.fake_popen_mock.call_args.args[0]
        assert "incus exec remote:remote-one" in command

    def test_non_default_project_run_shell_command(self):
        instances = [
            {
                "name": "remote-one",
                "status": "Running",
                "type": "container",
                "project": "special",
            },
        ]
        with patch("pyinfra.connectors.incus.local.shell", return_value=json.dumps(instances)):
            host = self.make_host("remote:remote-one")
            status, _ = host.run_shell_command("echo hi")
        assert status is True
        command = self.fake_popen_mock.call_args.args[0]
        assert "incus --project special exec remote:remote-one" in command

    def test_lxc_run_shell_command(self):
        host = self.make_host("vm-one", connector="lxc")
        status, _ = host.run_shell_command("echo hi")
        assert status is True
        command = self.fake_popen_mock.call_args.args[0]
        assert "lxc exec vm-one" in command

    def test_run_shell_command_success_exit_codes(self):
        self.fake_popen_mock().returncode = 1
        host = self.make_host()
        status, _ = host.run_shell_command("echo hi", _success_exit_codes=[1])
        assert status is True

    def test_run_shell_command_error(self):
        self.fake_popen_mock().returncode = 1
        host = self.make_host()
        status, _ = host.run_shell_command("echo hi")
        assert status is False

    def test_put_file(self):
        host = self.make_host()
        with patch("pyinfra.connectors.incus.os.remove") as remove:
            assert host.put_file("not-a-file", "/tmp/test file", print_output=True)
        remove.assert_called_once_with("__tempfile__")

        command = self.fake_popen_mock.call_args.args[0]
        expected = make_unix_command(
            "incus file push __tempfile__ 'container-one/tmp/test file'",
        ).get_raw_value()
        assert command == expected

    def test_put_file_error(self):
        self.fake_popen_mock().returncode = 1
        host = self.make_host()
        with self.assertRaises(OSError):
            host.put_file("not-a-file", "/tmp/test")

    def test_get_file(self):
        host = self.make_host()
        assert host.get_file("/tmp/test file", "not-a-file", print_output=True)
        command = self.fake_popen_mock.call_args.args[0]
        expected = make_unix_command(
            "incus file pull 'container-one/tmp/test file' __tempfile__",
        ).get_raw_value()
        assert command == expected

    def test_get_file_error(self):
        self.fake_popen_mock().returncode = 1
        host = self.make_host()
        with self.assertRaises(OSError):
            host.get_file("/tmp/test", "not-a-file")

    def test_file_io_objects(self):
        host = self.make_host()
        assert host.put_file(BytesIO(b"put"), "/tmp/put")

        output = BytesIO()
        assert host.get_file("/tmp/get", output)
        assert output.getvalue() == b"test!"
