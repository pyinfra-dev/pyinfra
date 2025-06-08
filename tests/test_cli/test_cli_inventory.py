from os import path

from pyinfra import inventory
from pyinfra.context import ctx_inventory, ctx_state

from ..paramiko_util import PatchSSHTestCase
from .util import run_cli


class TestCliInventory(PatchSSHTestCase):
    def test_load_deploy_group_data(self):
        ctx_state.reset()
        ctx_inventory.reset()

        hosts = ["somehost", "anotherhost", "someotherhost"]
        result = run_cli(
            "-y",
            ",".join(hosts),
            path.join("tests", "test_cli", "deploy", "deploy.py"),
            f'--chdir={path.join("tests", "test_cli", "deploy")}',
        )
        assert result.exit_code == 0, result.stdout

        assert inventory.data.get("hello") == "world"
        assert "leftover_data" in inventory.group_data
        assert inventory.group_data["leftover_data"].get("still_parsed") == "never_used"
        assert inventory.group_data["leftover_data"].get("_global_arg") == "gets_parsed"

    def test_load_group_data(self):
        ctx_state.reset()
        ctx_inventory.reset()

        hosts = ["somehost", "anotherhost", "someotherhost"]
        result = run_cli(
            "-y",
            ",".join(hosts),
            f'--group-data={path.join("tests", "test_cli", "deploy", "group_data")}',
            "exec",
            "uptime",
        )
        assert result.exit_code == 0, result.stdout

        assert inventory.data.get("hello") == "world"
        assert "leftover_data" in inventory.group_data
        assert inventory.group_data["leftover_data"].get("still_parsed") == "never_used"
        assert inventory.group_data["leftover_data"].get("_global_arg") == "gets_parsed"

    def test_load_group_data_file(self):
        ctx_state.reset()
        ctx_inventory.reset()

        hosts = ["somehost", "anotherhost", "someotherhost"]
        filename = path.join("tests", "test_cli", "deploy", "group_data", "leftover_data.py")
        result = run_cli(
            "-y",
            ",".join(hosts),
            f"--group-data={filename}",
            "exec",
            "uptime",
        )
        assert result.exit_code == 0, result.stdout

        assert "hello" not in inventory.data
        assert "leftover_data" in inventory.group_data
        assert inventory.group_data["leftover_data"].get("still_parsed") == "never_used"
        assert inventory.group_data["leftover_data"].get("_global_arg") == "gets_parsed"

    def test_ignores_variables_with_leading_underscore(self):
        ctx_state.reset()
        ctx_inventory.reset()

        result = run_cli(
            path.join("tests", "test_cli", "inventories", "invalid.py"),
            "exec",
            "--debug",
            "--",
            "echo hi",
        )

        assert result.exit_code == 0, result.stdout
        assert (
            'Ignoring variable "_hosts" in inventory file since it starts with a leading underscore'
            in result.stderr
        )
        assert inventory.hosts == {}

    def test_only_supports_list_and_tuples(self):
        ctx_state.reset()
        ctx_inventory.reset()

        result = run_cli(
            path.join("tests", "test_cli", "inventories", "invalid.py"),
            "exec",
            "--debug",
            "--",
            "echo hi",
        )

        assert result.exit_code == 0, result.stdout
        assert 'Ignoring variable "dict_hosts" in inventory file' in result.stderr, result.stdout
        assert (
            'Ignoring variable "generator_hosts" in inventory file' in result.stderr
        ), result.stdout
        assert inventory.hosts == {}

    def test_host_groups_may_only_contain_strings_or_tuples(self):
        ctx_state.reset()
        ctx_inventory.reset()

        result = run_cli(
            path.join("tests", "test_cli", "inventories", "invalid.py"),
            "exec",
            "--",
            "echo hi",
        )

        assert result.exit_code == 0, result.stdout
        assert 'Ignoring host group "issue_662"' in result.stderr, result.stdout
        assert inventory.hosts == {}
