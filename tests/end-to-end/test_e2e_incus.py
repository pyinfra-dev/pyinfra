import shlex
import subprocess
from time import sleep
from uuid import uuid4

import pytest


def _wait_for_agent(name):
    for _ in range(60):
        result = subprocess.run(
            f"incus exec {shlex.quote(name)} -- true",
            shell=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return
        sleep(1)
    raise AssertionError(f"Incus agent did not become ready on {name}")


@pytest.mark.end_to_end
@pytest.mark.end_to_end_incus
def test_int_incus_command_and_template(helpers, tmp_path):
    name = f"pyinfra-incus-{uuid4().hex}"
    helpers.run(f"incus launch images:alpine/3.21 {name}")

    try:
        helpers.run_check_output(
            f"pyinfra -y -v @incus/{name} server.shell 'echo incus-ok'",
            expected_lines=["incus-ok", "Errors: 0"],
        )

        template = tmp_path / "template.j2"
        template.write_text("hello incus\n")
        command = (
            f"pyinfra -y -v @incus/{name} files.template "
            f"src={shlex.quote(str(template))} dest=/tmp/incus-test"
        )
        helpers.run_check_output(command, expected_lines=["Success", "Errors: 0"])

        stdout, _ = helpers.run(f"incus exec {name} -- cat /tmp/incus-test")
        assert stdout == "hello incus\n"

        helpers.run_check_output(command, expected_lines=["No changes", "Errors: 0"])
    finally:
        helpers.run(f"incus delete --force {name}")


@pytest.mark.end_to_end
@pytest.mark.end_to_end_incus
def test_int_incus_vm(helpers):
    name = f"pyinfra-incus-vm-{uuid4().hex}"
    helpers.run(f"incus launch images:ubuntu/22.04/cloud {name} --vm")

    try:
        _wait_for_agent(name)
        helpers.run_check_output(
            f"pyinfra -y -v @incus/{name} server.shell 'echo incus-vm-ok'",
            expected_lines=["incus-vm-ok", "Errors: 0"],
        )
    finally:
        helpers.run(f"incus delete --force {name}")
