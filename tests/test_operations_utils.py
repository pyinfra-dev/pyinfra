from unittest import TestCase
from unittest.mock import MagicMock

import pytest

from pyinfra.facts.util.packages import PackageInfo, PackageStatus
from pyinfra.operations.util.docker import parse_image_reference, parse_registry
from pyinfra.operations.util.files import ensure_mode_int, unix_path_join
from pyinfra.operations.util.packaging import ensure_packages


class TestUnixPathJoin(TestCase):
    def test_simple_path(self):
        assert unix_path_join("home", "pyinfra") == "home/pyinfra"

    def test_absolute_path(self):
        assert unix_path_join("/", "home", "pyinfra") == "/home/pyinfra"

    def test_multiple_slash_path(self):
        assert unix_path_join("/", "home/", "pyinfra") == "/home/pyinfra"

    def test_end_slash_path(self):
        assert unix_path_join("/", "home", "pyinfra/") == "/home/pyinfra/"


class TestEnsureModeInt(TestCase):
    def test_int_passes_through(self):
        assert ensure_mode_int(644) == 644

    def test_plain_string(self):
        assert ensure_mode_int("644") == 644

    def test_zero_prefixed_string(self):
        assert ensure_mode_int("0644") == 644

    def test_octal_prefixed_string(self):
        assert ensure_mode_int("0o644") == 644

    def test_uppercase_octal_prefixed_string(self):
        assert ensure_mode_int("0O644") == 644

    def test_none_passes_through(self):
        assert ensure_mode_int(None) is None

    def test_symbolic_mode_passes_through(self):
        assert ensure_mode_int("u+x") == "u+x"

    def test_setuid_mode(self):
        assert ensure_mode_int("4755") == 4755

    def test_non_octal_int_raises(self):
        with pytest.raises(ValueError, match="non-octal digits"):
            ensure_mode_int(899)

    def test_non_octal_string_raises(self):
        with pytest.raises(ValueError, match="non-octal digits"):
            ensure_mode_int("0o899")


class TestParseRegistry(TestCase):
    def test_registry_with_port(self):
        """Test parsing registry with valid port number."""
        host, port = parse_registry("registry.io:5000")
        assert host == "registry.io"
        assert port == 5000

    def test_registry_without_port(self):
        """Test parsing registry without port."""
        host, port = parse_registry("registry.io")
        assert host == "registry.io"
        assert port is None

    def test_localhost_with_port(self):
        """Test parsing localhost with port."""
        host, port = parse_registry("localhost:8080")
        assert host == "localhost"
        assert port == 8080

    def test_ip_address_with_port(self):
        """Test parsing IP address with port."""
        host, port = parse_registry("192.168.1.100:5000")
        assert host == "192.168.1.100"
        assert port == 5000

    def test_invalid_port_raises_error(self):
        """Test that non-numeric port raises ValueError."""
        with pytest.raises(ValueError, match="Invalid port.*'abc' is not a valid port number"):
            parse_registry("registry.io:abc")

    def test_empty_port_raises_error(self):
        """Test that empty port raises ValueError."""
        with pytest.raises(ValueError, match="port cannot be empty"):
            parse_registry("registry.io:")

    def test_negative_port_raises_error(self):
        """Test that negative port raises ValueError."""
        with pytest.raises(ValueError, match="Invalid port number.*must be between 0 and 65535"):
            parse_registry("registry.io:-1")

    def test_port_too_large_raises_error(self):
        """Test that port > 65535 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid port number.*must be between 0 and 65535"):
            parse_registry("registry.io:65536")

    def test_float_port_raises_error(self):
        """Test that float port raises ValueError."""
        with pytest.raises(ValueError, match="Invalid port.*'5000.5' is not a valid port number"):
            parse_registry("registry.io:5000.5")


class TestParseImageReference(TestCase):
    def test_simple_repository(self):
        """Test parsing simple repository name."""
        ref = parse_image_reference("nginx")
        assert ref.repository == "nginx"
        assert ref.tag == "latest"
        assert ref.namespace is None
        assert ref.registry_host is None
        assert ref.registry_port is None
        assert ref.digest is None

    def test_repository_with_tag(self):
        """Test parsing repository with tag."""
        ref = parse_image_reference("nginx:1.21")
        assert ref.repository == "nginx"
        assert ref.tag == "1.21"
        assert ref.namespace is None
        assert ref.registry_host is None
        assert ref.registry_port is None
        assert ref.digest is None

    def test_repository_with_digest(self):
        """Test parsing repository with digest."""
        ref = parse_image_reference("nginx@sha256:abc123")
        assert ref.repository == "nginx"
        assert ref.digest == "sha256:abc123"
        assert ref.namespace is None
        assert ref.registry_host is None
        assert ref.registry_port is None
        assert ref.tag is None

    def test_repository_with_tag_and_digest(self):
        """Test parsing repository with both tag and digest."""
        ref = parse_image_reference("nginx:1.21@sha256:abc123")
        assert ref.repository == "nginx"
        assert ref.tag == "1.21"
        assert ref.digest == "sha256:abc123"
        assert ref.namespace is None
        assert ref.registry_host is None
        assert ref.registry_port is None

    def test_namespace_repository(self):
        """Test parsing namespace/repository."""
        ref = parse_image_reference("library/nginx")
        assert ref.repository == "nginx"
        assert ref.namespace == "library"
        assert ref.tag == "latest"
        assert ref.registry_host is None
        assert ref.registry_port is None
        assert ref.digest is None

    def test_namespace_repository_with_tag(self):
        """Test parsing namespace/repository:tag."""
        ref = parse_image_reference("library/nginx:1.21")
        assert ref.repository == "nginx"
        assert ref.namespace == "library"
        assert ref.tag == "1.21"
        assert ref.registry_host is None
        assert ref.registry_port is None
        assert ref.digest is None

    def test_registry_repository(self):
        """Test parsing registry.io/repository."""
        ref = parse_image_reference("registry.io/nginx")
        assert ref.repository == "nginx"
        assert ref.registry_host == "registry.io"
        assert ref.tag == "latest"
        assert ref.namespace is None
        assert ref.registry_port is None
        assert ref.digest is None

    def test_registry_with_port_repository(self):
        """Test parsing registry.io:5000/repository."""
        ref = parse_image_reference("registry.io:5000/nginx")
        assert ref.repository == "nginx"
        assert ref.registry_host == "registry.io"
        assert ref.registry_port == 5000
        assert ref.tag == "latest"
        assert ref.namespace is None
        assert ref.digest is None

    def test_registry_namespace_repository(self):
        """Test parsing registry.io/namespace/repository."""
        ref = parse_image_reference("registry.io/library/nginx")
        assert ref.repository == "nginx"
        assert ref.namespace == "library"
        assert ref.registry_host == "registry.io"
        assert ref.tag == "latest"
        assert ref.registry_port is None
        assert ref.digest is None

    def test_registry_with_port_namespace_repository(self):
        """Test parsing registry.io:5000/namespace/repository:tag."""
        ref = parse_image_reference("registry.io:5000/library/nginx:1.21")
        assert ref.repository == "nginx"
        assert ref.namespace == "library"
        assert ref.registry_host == "registry.io"
        assert ref.registry_port == 5000
        assert ref.tag == "1.21"
        assert ref.digest is None

    def test_nested_namespace(self):
        """Test parsing with nested namespace."""
        ref = parse_image_reference("registry.io/org/team/app:v1.0")
        assert ref.repository == "app"
        assert ref.namespace == "org/team"
        assert ref.registry_host == "registry.io"
        assert ref.tag == "v1.0"
        assert ref.registry_port is None
        assert ref.digest is None

    def test_localhost_registry(self):
        """Test parsing localhost registry."""
        ref = parse_image_reference("localhost:5000/myapp")
        assert ref.repository == "myapp"
        assert ref.registry_host == "localhost"
        assert ref.registry_port == 5000
        assert ref.tag == "latest"
        assert ref.namespace is None
        assert ref.digest is None

    def test_ip_address_registry(self):
        """Test parsing IP address registry."""
        ref = parse_image_reference("192.168.1.100:5000/myapp:latest")
        assert ref.repository == "myapp"
        assert ref.registry_host == "192.168.1.100"
        assert ref.registry_port == 5000
        assert ref.tag == "latest"
        assert ref.namespace is None
        assert ref.digest is None

    def test_complex_tag_with_colon_in_registry(self):
        """Test that colon in registry doesn't interfere with tag parsing."""
        ref = parse_image_reference("registry.io:5000/nginx:alpine-3.14")
        assert ref.repository == "nginx"
        assert ref.registry_host == "registry.io"
        assert ref.registry_port == 5000
        assert ref.tag == "alpine-3.14"
        assert ref.namespace is None
        assert ref.digest is None

    def test_property_name(self):
        """Test the name property."""
        ref = parse_image_reference("registry.io:5000/library/nginx:1.21")
        assert ref.repository == "nginx"
        assert ref.namespace == "library"
        assert ref.registry_host == "registry.io"
        assert ref.registry_port == 5000
        assert ref.tag == "1.21"
        assert ref.name == "registry.io:5000/library/nginx"
        assert ref.digest is None

    def test_property_registry(self):
        """Test the registry property."""
        ref = parse_image_reference("registry.io:5000/nginx")
        assert ref.repository == "nginx"
        assert ref.registry_host == "registry.io"
        assert ref.registry_port == 5000
        assert ref.tag == "latest"
        assert ref.registry == "registry.io:5000"
        assert ref.namespace is None
        assert ref.digest is None

    def test_property_registry_without_port(self):
        """Test the registry property without port."""
        ref = parse_image_reference("registry.io/nginx")
        assert ref.repository == "nginx"
        assert ref.registry_host == "registry.io"
        assert ref.tag == "latest"
        assert ref.registry == "registry.io"
        assert ref.namespace is None
        assert ref.registry_port is None
        assert ref.digest is None

    def test_property_full_reference(self):
        """Test the full_reference property."""
        ref = parse_image_reference("registry.io:5000/library/nginx:1.21@sha256:abc123")
        assert ref.repository == "nginx"
        assert ref.namespace == "library"
        assert ref.registry_host == "registry.io"
        assert ref.registry_port == 5000
        assert ref.tag == "1.21"
        assert ref.digest == "sha256:abc123"
        assert ref.full_reference == "registry.io:5000/library/nginx:1.21@sha256:abc123"

    def test_empty_image_raises_error(self):
        """Test that empty image raises ValueError."""
        with pytest.raises(ValueError, match="Image reference cannot be empty"):
            parse_image_reference("")

    def test_whitespace_only_image_raises_error(self):
        """Test that whitespace-only image raises ValueError."""
        with pytest.raises(ValueError, match="Image reference cannot be empty"):
            parse_image_reference("   ")

    def test_none_image_raises_error(self):
        """Test that None image raises ValueError."""
        with pytest.raises(ValueError, match="Image reference cannot be empty"):
            parse_image_reference(None)

    def test_invalid_registry_port_raises_error(self):
        """Test that invalid registry port raises ValueError."""
        with pytest.raises(ValueError, match="Invalid port.*'abc' is not a valid port number"):
            parse_image_reference("registry.io:abc/nginx")

    def test_whitespace_trimmed(self):
        """Test that whitespace is trimmed from input."""
        ref = parse_image_reference("  nginx:latest  ")
        assert ref.repository == "nginx"
        assert ref.tag == "latest"
        assert ref.namespace is None
        assert ref.registry_host is None
        assert ref.registry_port is None
        assert ref.digest is None

    def test_github_container_registry_image(self):
        """Test parsing GitHub Container Registry image."""
        ref = parse_image_reference("ghcr.io/owner/myapp:v1.2.3")
        assert ref.repository == "myapp"
        assert ref.namespace == "owner"
        assert ref.registry_host == "ghcr.io"
        assert ref.tag == "v1.2.3"
        assert ref.registry_port is None
        assert ref.digest is None


class TestEnsurePackagesDualFormat(TestCase):
    """ensure_packages must accept both dict[str, set[str]] and dict[str, PackageInfo]."""

    def _run(self, current_packages, packages=("vim",), latest=False, present=True):
        host = MagicMock()
        return list(
            ensure_packages(
                host,
                list(packages),
                current_packages,
                present=present,
                install_command="install",
                uninstall_command="uninstall",
                latest=latest,
                upgrade_command="upgrade",
            )
        ), host

    def test_old_format_installed_no_latest(self):
        commands, host = self._run({"vim": {"9.0"}}, latest=False)
        assert commands == []
        host.noop.assert_called_once_with("package vim is installed (9.0)")

    def test_old_format_multiple_versions_noop_is_sorted(self):
        # Sets are hash-randomized; the noop string must be deterministic.
        commands, host = self._run({"vim": {"9.0-1", "9.0"}}, latest=False)
        assert commands == []
        host.noop.assert_called_once_with("package vim is installed (9.0,9.0-1)")

    def test_old_format_latest_blindly_upgrades(self):
        commands, _ = self._run({"vim": {"9.0"}}, latest=True)
        assert commands == ["upgrade vim"]

    def test_old_format_missing_installs(self):
        commands, _ = self._run({}, latest=False)
        assert commands == ["install vim"]

    def test_new_format_installed_uses_status(self):
        current = {
            "vim": PackageInfo(
                name="vim", installed_versions=("9.0",), status=PackageStatus.INSTALLED
            )
        }
        commands, host = self._run(current, latest=False)
        assert commands == []
        host.noop.assert_called_once_with("package vim is installed (9.0)")

    def test_new_format_latest_only_upgrades_upgradeable(self):
        current = {
            "vim": PackageInfo(
                name="vim",
                installed_versions=("9.0",),
                available_version="9.1",
                status=PackageStatus.UPGRADEABLE,
            ),
            "git": PackageInfo(
                name="git", installed_versions=("2.40",), status=PackageStatus.INSTALLED
            ),
        }
        commands, host = self._run(current, packages=("vim", "git"), latest=True)
        assert commands == ["upgrade vim"]
        host.noop.assert_any_call("package git is up to date (2.40)")

    def test_new_format_held_is_noop_even_when_latest(self):
        current = {
            "vim": PackageInfo(
                name="vim",
                installed_versions=("9.0",),
                available_version="9.1",
                status=PackageStatus.HELD,
            )
        }
        commands, host = self._run(current, latest=True)
        assert commands == []
        host.noop.assert_called_once_with("package vim is held")

    def test_new_format_missing_installs(self):
        commands, _ = self._run({}, latest=False)
        assert commands == ["install vim"]

    def test_new_format_versioned_match_is_noop(self):
        current = {
            "vim": PackageInfo(
                name="vim", installed_versions=("9.0",), status=PackageStatus.INSTALLED
            )
        }
        host = MagicMock()
        commands = list(
            ensure_packages(
                host,
                ["vim=9.0"],
                current,
                present=True,
                install_command="install",
                uninstall_command="uninstall",
                latest=False,
                upgrade_command="upgrade",
                version_join="=",
            )
        )
        assert commands == []
        host.noop.assert_called_once_with("package vim is installed (9.0)")

    def test_new_format_versioned_mismatch_installs_pinned(self):
        current = {
            "vim": PackageInfo(
                name="vim", installed_versions=("9.0",), status=PackageStatus.INSTALLED
            )
        }
        host = MagicMock()
        commands = list(
            ensure_packages(
                host,
                ["vim=9.1"],
                current,
                present=True,
                install_command="install",
                uninstall_command="uninstall",
                latest=False,
                upgrade_command="upgrade",
                version_join="=",
            )
        )
        assert commands == ["install vim=9.1"]

    def test_new_format_upgradeable_with_pinned_version_installs_not_upgrades(self):
        current = {
            "vim": PackageInfo(
                name="vim",
                installed_versions=("9.0",),
                available_version="9.1",
                status=PackageStatus.UPGRADEABLE,
            )
        }
        host = MagicMock()
        commands = list(
            ensure_packages(
                host,
                ["vim=9.1"],
                current,
                present=True,
                install_command="install",
                uninstall_command="uninstall",
                latest=True,
                upgrade_command="upgrade",
                version_join="=",
            )
        )
        # Pinned-version request: install path, never upgrade path.
        assert commands == ["install vim=9.1"]

    def test_new_format_uninstall_removes_installed_package(self):
        current = {
            "vim": PackageInfo(
                name="vim", installed_versions=("9.0",), status=PackageStatus.INSTALLED
            )
        }
        commands, _ = self._run(current, present=False)
        assert commands == ["uninstall vim"]

    def test_new_format_uninstall_held_package_proceeds(self):
        # HELD blocks auto-upgrade, not explicit removal: uninstall must still proceed.
        current = {
            "vim": PackageInfo(name="vim", installed_versions=("9.0",), status=PackageStatus.HELD)
        }
        commands, _ = self._run(current, present=False)
        assert commands == ["uninstall vim"]

    def test_new_format_uninstall_missing_package_is_noop(self):
        commands, host = self._run({}, present=False)
        assert commands == []
        host.noop.assert_called_once_with("package vim is not installed")

    def test_new_format_multi_version_noop_lists_all_versions(self):
        # rpm-family installonly packages can have multiple installed versions.
        current = {
            "kernel": PackageInfo(
                name="kernel",
                installed_versions=("5.10.0-26", "6.1.0-13"),
                status=PackageStatus.INSTALLED,
            )
        }
        commands, host = self._run(current, packages=("kernel",), latest=False)
        assert commands == []
        host.noop.assert_called_once_with("package kernel is installed (5.10.0-26,6.1.0-13)")

    def test_new_format_multi_version_pinned_match_against_any_version(self):
        # Pinning to a non-highest installed version still counts as installed.
        current = {
            "kernel": PackageInfo(
                name="kernel",
                installed_versions=("5.10.0-26", "6.1.0-13"),
                status=PackageStatus.INSTALLED,
            )
        }
        host = MagicMock()
        commands = list(
            ensure_packages(
                host,
                ["kernel=5.10.0-26"],
                current,
                present=True,
                install_command="install",
                uninstall_command="uninstall",
                latest=False,
                upgrade_command="upgrade",
                version_join="=",
            )
        )
        assert commands == []
        host.noop.assert_called_once_with("package kernel is installed (5.10.0-26,6.1.0-13)")
