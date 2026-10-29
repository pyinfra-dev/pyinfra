import pytest
import testinfra
import testinfra.host


@pytest.fixture()
def docker_s6_image(helpers):
    # build integration test environment image; what we need is not available on any registry as far
    # as I can tell
    helpers.run(
        " ".join(
            [
                "docker build",
                # TODO remove
                "--network host",
                "--tag alpine-with-s6-overlay-and-frontend",
                "tests/end-to-end/s6",
            ]
        )
    )
    docker_container_id, _ = helpers.run(
        " ".join(
            [
                "docker run -d",
                "alpine-with-s6-overlay-and-frontend",
            ]
        )
    )
    # remove additional newline appended
    docker_container_id = docker_container_id.strip()
    try:
        yield docker_container_id
    finally:
        helpers.run(f"docker kill {docker_container_id}")


@pytest.mark.end_to_end
@pytest.mark.end_to_end_s6
def test_e2e_s6_set_copy(helpers):
    def check(host: testinfra.host.Host):
        assert (
            host.file("/var/lib/s6-rc/repository/sources/current").sha256sum
            == host.file("/var/lib/s6-rc/repository/sources/copy_of_current").sha256sum
        )

    helpers.run_container_test_host(
        "alpine-with-s6-overlay-and-frontend",
        "s6.set_copy copy_of_current source=current repodir=/var/lib/s6-rc/repository",
        check,
    )


# TODO set copy idempotency


@pytest.mark.end_to_end
@pytest.mark.end_to_end_s6
def test_e2e_s6_manage_set_prescriptions(helpers, docker_s6_image):
    helpers.run_check_output(
        f"pyinfra -y @docker/{docker_s6_image} "
        + 's6.manage_set \'[[], {"prescriptions": {"dbus-srv": "usable", "dbus-log": "usable", "polkit-srv": "usable", "polkit-log": "usable", "nix-daemon-srv": "active", "nix-daemon-log": "usable", "darkhttpd-srv": "active", "darkhttpd-log": "active"}}]\'',
        expected_lines=["docker build complete"],
    )

    host = testinfra.get_host(f"docker://{docker_s6_image}")
    status = host.check_output("s6-rc-set-status -r /var/lib/s6-rc/repository current")

    assert {
        "dbus-srv/usable",
        "dbus-log/usable",
        "polkit-srv/usable",
        "polkit-log/usable",
        "nix-daemon-srv/active",
        "nix-daemon-log/active",
        "darkhttpd-srv/active",
        "darkhttpd-log/active",
    } <= set(status.splitlines())


@pytest.mark.end_to_end
@pytest.mark.end_to_end_s6
def test_e2e_s6_manage_set_commit(helpers, docker_s6_image):
    host = testinfra.get_host(f"docker://{docker_s6_image}")
    # should be automatically created by s6 repo init by the Dockerfile
    # old_mtime = host.file("/var/lib/s6-rc/repository/compiled/current").mtime
    assert not host.file("/var/lib/s6-rc/repository/compiled/current").exists
    helpers.run_check_output(
        f"pyinfra -y @docker/{docker_s6_image} "
        + 's6.manage_set \'[[], {"the_set": "current", "do_commit": true, "prescriptions":{"darkhttpd-srv": "active", "darkhttpd-log": "active"}}]\'',
        expected_lines=["docker build complete"],
    )

    assert host.file("/var/lib/s6-rc/repository/compiled/current").exists


# no point to test idempotence, even if s6 set commit is idempotent, it is not considered
# "pyinfra-idempotent", as commit_set ooption for manage_set always yields a command
# @pytest.mark.end_to_end
# @pytest.mark.end_to_end_s6
# def test_e2e_s6_manage_set_commit_semi_idempotence(helpers, docker_s6_image):
#    host = testinfra.get_host(f"docker://{docker_s6_image}")
#    host.run_expect([0], "s6 set enable top")
#    host.run_expect([0], "s6 set commit")
#    old_mtime = host.file("/var/lib/s6-rc/repository/compiled/current").mtime
#    helpers.run_check_output(
#        f"pyinfra -y @docker/{docker_s6_image} " + 's6.manage_set \'[[], {"the_set": "current", "do_commit": true}]\'',
#        expected_lines=["docker build complete"],
#    )
#    new_mtime = host.file("/var/lib/s6-rc/repository/compiled/current").mtime
#
#    assert new_mtime == old_mtime


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_manage_set_install(helpers):
    pass


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_manage_set_commit_install(helpers):
    pass


# present=True where a set did not exist previously
@pytest.mark.end_to_end
@pytest.mark.end_to_end_s6
def test_e2e_s6_manage_set_create(helpers):
    def check(host: testinfra.host.Host):
        assert host.file("/var/lib/s6-rc/repository/sources/new_set").exists

    helpers.run_container_test_host(
        "alpine-with-s6-overlay-and-frontend",
        "s6.manage_set the_set=new_set",
        check,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_s6
def test_e2e_s6_manage_set_delete(helpers):
    def check(host: testinfra.host.Host):
        assert not host.file("/var/lib/s6-rc/repository/sources/current").exists

    helpers.run_container_test_host(
        "alpine-with-s6-overlay-and-frontend",
        "s6.manage_set the_set=current present=False",
        check,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_s6
def test_e2e_s6_stop_services(helpers):
    def check(host: testinfra.host.Host):
        status = host.check_output("s6-rc -c list")
        print(status.splitlines())
        # assert "dbus-srv/longrun/down/explicit" in status.splitlines()
        assert {
            "nix-daemon-srv/longrun//down/",
            "nix-daemon-log/longrun//down/",
            "polkit-srv/longrun//down/",
            "polkit-log/longrun//down/",
            "dbus-srv/longrun//down/",
            "dbus-log/longrun//down/",
        } <= set(status.splitlines())

    helpers.run_container_test_host(
        "alpine-with-s6-overlay-and-frontend",
        's6.service \'[[["nix-daemon-srv", "nix-daemon-log", "polkit-srv", "polkit-log", "dbus-srv", "dbus-log"]], {"running": false}]\'',
        check,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_s6
def test_e2e_s6_start_services_idempotence(helpers, docker_s6_image):
    host = testinfra.get_host(f"docker://{docker_s6_image}")

    # test if it starts the services
    helpers.run_check_output(
        f"pyinfra -y @docker/{docker_s6_image} "
        + 's6.service \'[[["nix-daemon-srv", "nix-daemon-log"]], {"running": true}]\'',
        expected_lines=["docker build complete"],
    )
    status = host.check_output("s6-rc -a list")
    assert {
        "dbus-srv",
        "dbus-log",
        "polkit-srv",
        "polkit-log",
        "nix-daemon-srv",
        "nix-daemon-log",
    } <= set(status.splitlines())

    # test for idempotence
    helpers.run_check_output(
        f"pyinfra -y @docker/{docker_s6_image} "
        + 's6.service \'[[["nix-daemon-srv", "nix-daemon-log"]], {"running": true}]\'',
        expected_lines=["docker build complete"],
    )
    status_new = host.check_output("s6-rc -a list")
    assert status == status_new


@pytest.mark.end_to_end
@pytest.mark.end_to_end_s6
def test_e2e_s6_service_enable_idempotence(helpers, docker_s6_image):
    host = testinfra.get_host(f"docker://{docker_s6_image}")

    # base test
    host.run_expect([0], "s6 set disable nix-daemon-srv nix-daemon-log darkhttpd-srv darkhttpd-log")
    helpers.run_check_output(
        f"pyinfra -y @docker/{docker_s6_image} "
        + 's6.service \'[[["nix-daemon-srv", "nix-daemon-log", "darkhttpd-srv", "darkhttpd-log"]], {"enabled": true}]\'',
        expected_lines=["docker build complete"],
    )
    old_enabled = host.check_output(
        "s6 set status nix-daemon-srv nix-daemon-log darkhttpd-srv darkhttpd-log"
    )

    assert {
        "nix-daemon-srv/active",
        "nix-daemon-log/active",
        "darkhttpd-srv/active",
        "darkhttpd-log/active",
    } <= set(old_enabled.splitlines())

    # idempotence
    new_enabled = host.check_output(
        "s6 set status nix-daemon-srv nix-daemon-log darkhttpd-srv darkhttpd-log"
    )

    assert set(old_enabled.splitlines()) == set(new_enabled.splitlines())


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_service_disable(helpers):
    pass


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_service_enable_always(helpers):
    pass


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_service_enable_masked(helpers):
    pass


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_service_enable_commit_install(helpers):
    pass
