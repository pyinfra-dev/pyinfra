from unittest import TestCase

import pytest

from pyinfra.operations.util.docker import parse_image_reference, parse_registry
from pyinfra.operations.util.files import unix_path_join


class TestUnixPathJoin(TestCase):
    def test_simple_path(self):
        assert unix_path_join("home", "pyinfra") == "home/pyinfra"

    def test_absolute_path(self):
        assert unix_path_join("/", "home", "pyinfra") == "/home/pyinfra"

    def test_multiple_slash_path(self):
        assert unix_path_join("/", "home/", "pyinfra") == "/home/pyinfra"

    def test_end_slash_path(self):
        assert unix_path_join("/", "home", "pyinfra/") == "/home/pyinfra/"


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
