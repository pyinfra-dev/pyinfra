import pytest


@pytest.mark.int
def test_int_docker_install_package_ubuntu(helpers):
    helpers.run(
        'pyinfra -v @docker/ubuntu:18.04 apt.packages iftop sudo=true update=true',
        expected_lines=['is in beta'],
    )


@pytest.mark.int
def test_int_docker_apk_on_alpine(helpers):
    helpers.run(
        'pyinfra -v @docker/alpine:3.11 apk.py',
        expected_lines=['is in beta'],
    )


@pytest.mark.int
def test_int_docker_apt_and_npm_on_ubuntu(helpers):
    helpers.run(
        'pyinfra -v @docker/ubuntu:18.04 apt.py npm.py',
        expected_lines=['is in beta'],
    )


@pytest.mark.int
def test_int_docker_git_gem_and_pip_on_mult(helpers):
    helpers.run(
        (
            'pyinfra -v '
            '@docker/ubuntu:18.04,@docker/centos:8,@docker/alpine:3.11 '
            'git.py gem.py pip.py'
        ),
        expected_lines=['is in beta'],
    )


@pytest.mark.int
def test_int_docker_pacman_on_arch(helpers):
    helpers.run(
        'pyinfra -v @docker/archlinux pacman.py',
        expected_lines=['is in beta'],
    )


@pytest.mark.int
def test_int_docker_files_dnf_server_on_centos(helpers):
    helpers.run(
        'pyinfra -v @docker/centos:8 files.py dnf.py server.py',
        expected_lines=['is in beta'],
    )


@pytest.mark.int
def test_int_docker_yum_on_centos(helpers):
    helpers.run(
        'pyinfra -v @docker/centos:8 yum.py',
        expected_lines=['is in beta'],
    )


@pytest.mark.int
def test_int_docker_adhoc_apt_packages(helpers):
    helpers.run(
        'pyinfra -v @docker/ubuntu:18.04 apt.packages iftop sudo=true update=true',
        expected_lines=['is in beta'],
    )


@pytest.mark.int
def test_int_docker_adhoc_fact_os(helpers):
    helpers.run(
        'pyinfra -v @docker/ubuntu:18.04,@docker/centos:8 fact os',
        expected_lines=['Gathering facts', 'Fact data', 'is in beta'],
    )


@pytest.mark.int
def test_int_docker_adhoc_all_facts(helpers):
    helpers.run(
        'pyinfra -v @docker/ubuntu:18.04,@docker/centos:8 all-facts',
        expected_lines=['Gathering facts', 'Loaded fact', 'is in beta'],
    )
