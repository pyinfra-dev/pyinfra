'''
Docker based integration tests - these tests ensure the examples work as expected with the given
Docker images. Note that these sometimes break due to Docker image changes (ideally we use the
most-specific tag available for each image to reduce/avoid this problem).
'''

import pytest


@pytest.mark.int
@pytest.mark.docker
def test_int_docker_install_package_ubuntu(helpers):
    helpers.run(
        'pyinfra @docker/ubuntu:18.04 apt.packages iftop update=true',
        expected_lines=['docker build complete'],
    )


@pytest.mark.int
@pytest.mark.docker
def test_int_docker_apk_on_alpine(helpers):
    helpers.run(
        'pyinfra @docker/alpine:3.11 apk.py',
        expected_lines=['docker build complete'],
    )


@pytest.mark.int
@pytest.mark.docker
def test_int_docker_apt_and_npm_on_ubuntu(helpers):
    helpers.run(
        'pyinfra @docker/ubuntu:18.04 apt.py npm.py',
        expected_lines=['docker build complete'],
    )


@pytest.mark.int
@pytest.mark.docker
def test_int_docker_git_gem_and_pip_on_mult(helpers):
    helpers.run(
        (
            'pyinfra '
            '@docker/ubuntu:18.04,@docker/alpine:3.11 '
            'git.py gem.py pip.py'
        ),
        expected_lines=['docker build complete'],
    )


@pytest.mark.int
@pytest.mark.docker
def test_int_docker_pacman_on_arch(helpers):
    helpers.run(
        'pyinfra @docker/archlinux:base-20220102.0.42924 pacman.py',
        expected_lines=['docker build complete'],
    )


@pytest.mark.int
@pytest.mark.docker
def test_int_docker_yum_on_centos(helpers):
    helpers.run(
        'pyinfra @docker/centos:7.9.2009 yum.py',
        expected_lines=['docker build complete'],
    )


@pytest.mark.int
@pytest.mark.docker
def test_int_docker_adhoc_fact_os(helpers):
    helpers.run(
        'pyinfra @docker/ubuntu:18.04,@docker/centos:7.9.2009 fact os',
        expected_lines=['Gathering facts', 'Fact data'],
    )


@pytest.mark.int
@pytest.mark.docker
def test_int_docker_adhoc_all_facts(helpers):
    helpers.run(
        'pyinfra @docker/ubuntu:18.04,@docker/centos:7.9.2009 all-facts',
        expected_lines=['Gathering facts', 'Loaded fact'],
    )
