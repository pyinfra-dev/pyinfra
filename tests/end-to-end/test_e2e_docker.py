"""
Docker based integration tests.
"""

import pytest
import testinfra
import testinfra.host


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_docker_install_package_ubuntu(helpers):
    def check(host: testinfra.host.Host):
        assert host.package("iftop").is_installed

    helpers.run_container_test_host(
        "ubuntu:22.04",
        "apt.packages packages=iftop update=true",
        check,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_docker_file(helpers):
    def check(host: testinfra.host.Host):
        file = host.file("/testfile")
        assert file.is_file
        assert file.user == "nobody"
        assert file.group == "root"
        assert file.mode == 0o755

    helpers.run_container_test_host(
        "ubuntu:22.04",
        "files.file path=/testfile mode=755 user=nobody",
        check,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_docker_put_file(helpers):
    # TODO: why does importing this at top level break things?
    from pyinfra.api.util import get_file_sha256

    with open("README.md", "r") as f:
        expected_sum = get_file_sha256(f)

    def check(host: testinfra.host.Host):
        file = host.file("/README.md")
        assert file.is_file
        assert file.sha256sum == expected_sum

    helpers.run_container_test_host(
        "ubuntu:22.04",
        "files.put src=README.md dest=README.md mode=755 user=nobody",
        check,
    )
