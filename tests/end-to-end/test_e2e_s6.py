import pytest
import testinfra
import testinfra.host


@pytest.fixture()
def docker_s6_overlay_image(helpers):
    # build image
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
        " ".join(["docker run -d", "alpine-with-s6-overlay-and-frontend"])
    )
    try:
        yield docker_container_id
    finally:
        helpers.run(f"docker kill {docker_container_id}")


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_set_copy(helpers):
    pass


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_manage_set_prescriptions(helpers):
    pass


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_manage_set_commit(helpers):
    pass


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
@pytest.mark.end_to_end_docker
def test_e2e_s6_manage_set_create(helpers):
    pass


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_manage_set_delete(helpers):
    pass


@pytest.mark.end_to_end
@pytest.mark.end_to_end_s6
def test_e2e_s6_stop_services(helpers, docker_s6_overlay_image):
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
def test_e2e_s6_start_services(helpers, docker_s6_overlay_image):
    def check(host: testinfra.host.Host):
        for servicedir in [
            "/run/s6-rc/scandir/" + srv
            for srv in [
                "nix-daemon-srv",
                "nix-daemon-log",
                "darkhttpd-srv",
                "darkhttpd-log",
            ]
        ]:
            assert host.file(servicedir + "/down").exists

    helpers.run_container_test_host(
        "alpine-with-s6-overlay-and-frontend",
        # running=True is the default, and specifying it in the {} gives an error
        's6.service \'[["nix-daemon-srv", "nix-daemon-log", "darkhttpd-srv", "darkhttpd-log"], {}]\'',
        check,
    )


# not idempotent
@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_service_restart(helpers):
    pass


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_service_reload(helpers):
    pass


@pytest.mark.end_to_end
@pytest.mark.end_to_end_docker
def test_e2e_s6_service_enable(helpers):
    pass


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
