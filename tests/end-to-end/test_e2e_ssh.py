"""
SSH integration tests - mostly checking for idempotency on file operations.
"""

import os
import time
from getpass import getuser

import pytest

DOCKER_IMAGE = (
    "linuxserver/openssh-server@sha256:"
    "1e33f77de1021dcd2e52a6bbc787082abfb591416a00e6a1422b83b3b426f09d"
)

PYINFRA_COMMAND = (
    "pyinfra -y -v localhost "
    "--ssh-port 2222 "
    "--ssh-user pyinfra "
    "--ssh-password password "
    "--data ssh_known_hosts_file=/dev/null "
    "--data ssh_strict_host_key_checking=no "
)


@pytest.fixture(autouse=True)
def run_docker_ssh_server(helpers):
    docker_container_id, _ = helpers.run(
        " ".join(
            [
                "docker run -d",
                "-p 2222:2222",
                "-e PASSWORD_ACCESS=true",
                "-e USER_PASSWORD=password",
                "-e USER_NAME=pyinfra",
                "-e SUDO_ACCESS=true",
                DOCKER_IMAGE,
            ],
        ),
    )
    time.sleep(10)  # allow openSSH to start
    try:
        yield docker_container_id
    finally:
        helpers.run(f"docker kill {docker_container_id}")


@pytest.mark.end_to_end
@pytest.mark.end_to_end_ssh
def test_e2e_ssh_sudo_password(helpers):
    helpers.run_check_output(
        f"{PYINFRA_COMMAND} server.shell echo _sudo=True _sudo_password=password",
        expected_lines=["localhost] Success"],
    )
    helpers.run_check_output(
        f"{PYINFRA_COMMAND} server.shell echo _sudo=True _sudo_password=wrongpassword",
        expected_lines=["localhost] Error"],
        expected_exit_code=1,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_ssh
def test_int_local_file_no_changes(helpers):
    helpers.run_check_output(  # first run = create the file
        f"{PYINFRA_COMMAND} files.file _testfile",
        expected_lines=["localhost] Success"],
    )

    helpers.run_check_output(  # second run = no changes
        f"{PYINFRA_COMMAND} files.file _testfile",
        expected_lines=["localhost] No changes"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_ssh
def test_int_local_directory_no_changes(helpers):
    helpers.run_check_output(  # first run = create the directory
        f"{PYINFRA_COMMAND} files.directory _testdir",
        expected_lines=["localhost] Success"],
    )

    helpers.run_check_output(  # second run = no changes
        f"{PYINFRA_COMMAND} files.directory _testdir",
        expected_lines=["localhost] No changes"],
    )

    helpers.run_check_output(  # third run (remove) = remove directory
        f"{PYINFRA_COMMAND} files.directory _testdir present=False",
        expected_lines=["localhost] Success"],
    )

    helpers.run_check_output(  # fourth run (remove) = no chances
        f"{PYINFRA_COMMAND} files.directory _testdir present=False",
        expected_lines=["localhost] No changes"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_ssh
def test_int_local_link_no_changes(helpers):
    helpers.run_check_output(  # first run = create the link
        f"{PYINFRA_COMMAND} files.link _testlink target=_testfile",
        expected_lines=["localhost] Success"],
    )

    helpers.run_check_output(  # second run = no changes
        f"{PYINFRA_COMMAND} files.link _testlink target=_testfile",
        expected_lines=["localhost] No changes"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_ssh
def test_int_local_line_no_changes(helpers):
    helpers.run_check_output(  # first run = create the line
        f"{PYINFRA_COMMAND} files.line _testfile someline",
        expected_lines=["localhost] Success"],
    )

    helpers.run_check_output(  # second run = no changes
        f"{PYINFRA_COMMAND} files.line _testfile someline",
        expected_lines=["localhost] No changes"],
    )

    helpers.run_check_output(  # replace the line
        f"{PYINFRA_COMMAND} files.line _testfile someline replace=anotherline",
        expected_lines=["localhost] Success"],
    )

    helpers.run_check_output(  # second run replace the line = no changes
        f"{PYINFRA_COMMAND} files.line _testfile someline replace=anotherline",
        expected_lines=["localhost] No changes"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_ssh
@pytest.mark.skipif(
    not os.getenv("PYINFRA_E2E_SSH_LOCALHOST"),
    reason="Set PYINFRA_E2E_SSH_LOCALHOST=1 to enable localhost SSH test",
)
def test_e2e_ssh_localhost_ansible_module(helpers):
    ssh_user = os.getenv("PYINFRA_E2E_SSH_USER", getuser())
    ssh_key = os.path.expanduser(os.getenv("PYINFRA_E2E_SSH_KEY", "~/.ssh/id_ed25519"))

    if not os.path.isfile(ssh_key):
        pytest.skip(f"SSH key not found: {ssh_key}")

    command = (
        "pyinfra -y -v localhost "
        f"--ssh-user {ssh_user} "
        f"--ssh-key {ssh_key} "
        "--data ssh_allow_agent=false "
        "--data ssh_known_hosts_file=/dev/null "
        "--data ssh_strict_host_key_checking=no "
        "ansible.module examples/ansible_modules/ping.py data=pyinfra"
    )

    helpers.run_check_output(
        command,
        expected_lines=["localhost] Success"],
    )
