"""
Podman based integration tests.
"""

import pytest


@pytest.mark.end_to_end
@pytest.mark.end_to_end_podman
def test_int_podman_install_package_ubuntu(helpers):
    helpers.run_check_output(
        "pyinfra -y --chdir examples @podman/ubuntu:22.04 apt.packages iftop update=true",
        expected_lines=["podman build complete"],
    )
