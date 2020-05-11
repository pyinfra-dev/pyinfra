import pytest


@pytest.mark.int
def test_int_docker_install_package_ubuntu(helpers):
    '''Test docker'''
    helpers.run('pyinfra @docker/ubuntu:18.04 apt.packages iftop sudo=true update=true',
                expected_stderr_lines=['is in beta'])


@pytest.mark.int
def test_int_docker_apk_on_alpine(helpers):
    '''Test docker'''
    helpers.run('pyinfra @docker/alpine:3.11 apk.py',
                expected_stderr_lines=['is in beta'])


@pytest.mark.int
def test_int_docker_apt_and_npm_on_ubuntu(helpers):
    '''Test docker'''
    helpers.run('pyinfra @docker/ubuntu:18.04 apt.py npm.py',
                expected_stderr_lines=['is in beta'])


@pytest.mark.int
def test_int_docker_git_gem_and_pip_on_mult(helpers):
    '''Test docker'''
    helpers.run('pyinfra @docker/ubuntu:18.04,@docker/centos:8,'
                '@docker/alpine:3.11 git.py gem.py pip.py',
                expected_stderr_lines=['is in beta'])


@pytest.mark.int
def test_int_docker_pacman_on_arch(helpers):
    '''Test docker'''
    helpers.run('pyinfra @docker/archlinux pacman.py',
                expected_stderr_lines=['is in beta'])


@pytest.mark.int
def test_int_docker_files_dnf_server_on_centos(helpers):
    '''Test docker'''
    helpers.run('pyinfra @docker/centos:8 files.py dnf.py server.py',
                expected_stderr_lines=['is in beta'])


@pytest.mark.int
def test_int_docker_yum_on_centos(helpers):
    '''Test docker'''
    helpers.run('pyinfra @docker/centos:8 yum.py',
                expected_stderr_lines=['is in beta'])


@pytest.mark.int
def test_int_docker_adhoc_apt_packages(helpers):
    '''Test docker'''
    helpers.run('pyinfra @docker/ubuntu:18.04 apt.packages iftop sudo=true update=true',
                expected_stderr_lines=['is in beta'])


@pytest.mark.int
def test_int_docker_adhoc_fact_os(helpers):
    '''Test docker'''
    helpers.run('pyinfra @docker/ubuntu:18.04,@docker/centos:8 fact os',
                expected_stdout_lines=['Gathering facts', 'Fact data'],
                expected_stderr_lines=['is in beta'])


@pytest.mark.int
def test_int_docker_adhoc_all_facts(helpers):
    '''Test docker'''
    helpers.run('pyinfra @docker/ubuntu:18.04,@docker/centos:8 all-facts',
                expected_stdout_lines=['Gathering facts', 'Loaded fact'],
                expected_stderr_lines=['is in beta'])
