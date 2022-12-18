"""
Docker based integration tests - these tests ensure the examples work as expected with the given
Docker images. Note that these sometimes break due to Docker image changes (ideally we use the
most-specific tag available for each image to reduce/avoid this problem).
"""

import pytest


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_docker_install_package_ubuntu(helpers):
    helpers.run_check_output(
        "pyinfra --chdir examples @docker/ubuntu:18.04 apt.packages iftop update=true",
        expected_lines=["docker build complete"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_docker_apk_on_alpine(helpers):
    helpers.run_check_output(
        "pyinfra --chdir examples @docker/alpine:3.11 apk.py",
        expected_lines=["docker build complete"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_docker_apt_and_npm_on_ubuntu(helpers):
    helpers.run_check_output(
        "pyinfra --chdir examples @docker/ubuntu:18.04 apt.py npm.py",
        expected_lines=["docker build complete"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_docker_git_gem_and_pip_on_mult(helpers):
    helpers.run_check_output(
        (
            "pyinfra --chdir examples "
            "@docker/ubuntu:18.04,@docker/alpine:3.11 "
            "git.py gem.py pip.py"
        ),
        expected_lines=["docker build complete"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_docker_pacman_on_arch(helpers):
    helpers.run_check_output(
        # ArchLinux is continuously updated so using latest here seems most sensible
        "pyinfra --chdir examples @docker/archlinux:latest pacman.py",
        expected_lines=["docker build complete"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_docker_yum_on_centos(helpers):
    helpers.run_check_output(
        "pyinfra --chdir examples @docker/centos:7.9.2009 yum.py",
        expected_lines=["docker build complete"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_int_docker_adhoc_fact_os(helpers):
    helpers.run_check_output(
        "pyinfra --chdir examples @docker/ubuntu:18.04,@docker/centos:7.9.2009 fact server.Os",
        expected_lines=["Gathering facts", "Fact data"],
    )
