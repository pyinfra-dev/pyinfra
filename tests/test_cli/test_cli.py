from __future__ import annotations

from os import path

from .util import run_cli


def test_cli_help():
    assert run_cli("--help").exit_code == 0


def test_cli_version():
    assert run_cli("--version").exit_code == 0


def test_cli_executes_deploy(fake_asyncssh):
    deploy_dir = path.join("tests", "test_cli", "deploy")
    inventory_path = path.join(deploy_dir, "inventories", "inventory.py")
    deploy_path = path.join(deploy_dir, "deploy.py")

    result = run_cli(
        "-y",
        inventory_path,
        deploy_path,
        f"--chdir={deploy_dir}",
    )

    assert result.exit_code == 0, result.stderr
    for connection in fake_asyncssh.values():
        assert connection.commands_run, "expected CLI deploy to execute commands"
