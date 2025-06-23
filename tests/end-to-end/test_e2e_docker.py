"""
Docker based integration tests.
"""

import pytest


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_docker_install_package_ubuntu(helpers):
    helpers.run_check_output(
        "pyinfra -y --chdir examples @docker/ubuntu:22.04 apt.packages iftop update=true",
        expected_lines=["docker build complete"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_podman_install_package_ubuntu(helpers):
    helpers.run_check_output(
        "pyinfra -y --chdir examples @podman/ubuntu:22.04 apt.packages iftop update=true",
        expected_lines=["podman build complete"],
    )
