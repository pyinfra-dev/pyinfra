from os import path
from unittest import TestCase

from pyinfra.context import ctx_state
from pyinfra_cli.main import _main

from ..paramiko_util import PatchSSHTestCase
from .util import run_cli


class TestCliEagerFlags(TestCase):
    def test_print_help(self):
        result = run_cli("--version")
        assert result.exit_code == 0, result.stdout

        result = run_cli("--help")
        assert result.exit_code == 0, result.stdout


class TestDeployCli(PatchSSHTestCase):
    def setUp(self):
        ctx_state.reset()

    def test_invalid_deploy(self):
        result = run_cli(
            "@local",
            "not-a-file.py",
        )
        assert result.exit_code == 1, result.stdout
        assert "No deploy file: not-a-file.py" in result.stdout


class TestOperationCli(PatchSSHTestCase):
    def test_invalid_operation_module(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "not_a_module.shell",
        )
        assert result.exit_code == 1, result.stdout
        assert "No such module: not_a_module"

    def test_invalid_operation_function(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "server.not_an_operation",
        )
        assert result.exit_code == 1, result.stdout
        assert "No such operation: server.not_an_operation"

    def test_deploy_operation(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "server.shell",
            "echo hi",
        )
        assert result.exit_code == 0, result.stdout

    def test_deploy_operation_with_all(self):
        result = run_cli(
            path.join("tests", "deploy", "inventory_all.py"),
            "server.shell",
            "echo hi",
        )
        assert result.exit_code == 0, result.stdout

    def test_deploy_operation_json_args(self):
        result = run_cli(
            path.join("tests", "deploy", "inventory_all.py"),
            "server.shell",
            '[["echo hi"], {}]',
        )
        assert result.exit_code == 0, result.stdout


class TestFactCli(PatchSSHTestCase):
    def test_get_fact(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "fact",
            "server.Os",
        )
        assert result.exit_code == 0, result.stdout
        assert '"somehost": null' in result.stdout

    def test_get_fact_with_kwargs(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "fact",
            "files.File",
            "path=.",
        )
        assert result.exit_code == 0, result.stdout
        assert '"somehost": null' in result.stdout

    def test_invalid_fact_module(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "fact",
            "not_a_module.NotAFact",
        )
        assert result.exit_code == 1, result.stdout
        assert "No such module: pyinfra.facts.not_a_module" in result.stdout

    def test_invalid_fact_class(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "fact",
            "server.NotAFact",
        )
        assert result.exit_code == 1, result.stdout
        assert "No such attribute in module pyinfra.facts.server: NotAFact" in result.stdout


class TestExecCli(PatchSSHTestCase):
    def test_exec_command(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "exec",
            "--",
            "echo hi",
        )
        assert result.exit_code == 0, result.stdout

    def test_exec_command_with_options(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "exec",
            "--sudo",
            "--sudo-user",
            "pyinfra",
            "--su-user",
            "pyinfrawhat",
            "--port",
            "1022",
            "--user",
            "ubuntu",
            "--",
            "echo hi",
        )
        assert result.exit_code == 0, result.stdout

    def test_exec_command_with_serial(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "exec",
            "--serial",
            "--",
            "echo hi",
        )
        assert result.exit_code == 0, result.stdout

    def test_exec_command_with_no_wait(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "exec",
            "--no-wait",
            "--",
            "echo hi",
        )
        assert result.exit_code == 0, result.stdout

    def test_exec_command_with_debug_operations(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "exec",
            "--debug-operations",
            "--",
            "echo hi",
        )
        assert result.exit_code == 0, result.stdout

    def test_exec_command_with_debug_facts(self):
        result = run_cli(
            path.join("tests", "deploy", "inventories", "inventory.py"),
            "exec",
            "--debug-facts",
            "--",
            "echo hi",
        )
        assert result.exit_code == 0, result.stdout


class TestDirectMainExecution(PatchSSHTestCase):
    """
    These tests are very similar as above, without the click wrappers - basically
    here because coverage.py fails to properly detect all the code under the wrapper.
    """

    def test_deploy_operation_direct(self):
        with self.assertRaises(SystemExit) as e:
            _main(
                inventory=path.join("tests", "test_deploy", "inventories", "inventory.py"),
                operations=["server.shell", "echo hi"],
                chdir=None,
                group_data=None,
                verbosity=0,
                ssh_user=None,
                ssh_port=None,
                ssh_key=None,
                ssh_key_password=None,
                ssh_password=None,
                sudo=False,
                sudo_user=None,
                use_sudo_password=False,
                su_user=None,
                parallel=None,
                fail_percent=0,
                dry=False,
                limit=None,
                no_wait=False,
                serial=False,
                winrm_username=None,
                winrm_password=None,
                winrm_port=None,
                winrm_transport=None,
                shell_executable=None,
                quiet=False,
                data=tuple(),
                debug=False,
                debug_facts=False,
                debug_operations=False,
                config_filename="config.py",
            )
            assert e.args == (0,)
